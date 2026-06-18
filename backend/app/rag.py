import logging
from pathlib import Path
from typing import Optional

from langchain_chroma import Chroma
from langchain_community.document_loaders import (
    DirectoryLoader,
    TextLoader,
    Docx2txtLoader,
    UnstructuredPowerPointLoader,
)
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.date_utils import resolve_query_date
from app.ingestion import load_all_documents, log_chunk_summary
from app.schemas import HistoryTurn

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self):
        self.vectorstore: Optional[Chroma] = None
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

    def load_documents(self) -> list[Document]:
        return load_all_documents()

    def build_vectorstore(self, persist: bool = False):
        raw_docs = self.load_documents()
        if not raw_docs:
            logger.warning("No documents loaded from %s", settings.DOCS_DIR)

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            add_start_index=True,
        )
        splits = splitter.split_documents(raw_docs)
        log_chunk_summary(splits)

        persist_directory = str(settings.CHROMA_DB_DIR) if persist else None
        
        self.vectorstore = Chroma.from_documents(
            documents=splits,
            embedding=self.embeddings,
            collection_name="practi_kb",
            persist_directory=persist_directory,
        )
        logger.info(
            "Chroma index built with %s chunks from %s files. Persisted: %s", 
            len(splits), len(raw_docs), persist
        )

    def load_vectorstore(self):
        if not settings.CHROMA_DB_DIR.exists():
            logger.info("Chroma DB directory not found at %s. Building from docs...", settings.CHROMA_DB_DIR)
            self.build_vectorstore(persist=True)
            return

        self.vectorstore = Chroma(
            collection_name="practi_kb",
            embedding_function=self.embeddings,
            persist_directory=str(settings.CHROMA_DB_DIR),
        )
        logger.info("Loaded persisted Chroma index from %s", settings.CHROMA_DB_DIR)

    def history_to_messages(self, history: list[HistoryTurn]) -> list[BaseMessage]:
        out: list[BaseMessage] = []
        for turn in history:
            if turn.role == "user":
                out.append(HumanMessage(content=turn.content))
            else:
                out.append(AIMessage(content=turn.content))
        return out

    def _is_future_doc(self, doc: Document, query_date: str) -> bool:
        doc_date = doc.metadata.get("doc_date", "unknown")
        return doc_date != "unknown" and doc_date > query_date

    def retrieve(self, message: str, query_date: str) -> list[Document]:
        """Retrieve by relevance; only exclude documents dated after the query."""
        if self.vectorstore is None:
            raise ValueError("Vector store not initialized")

        k = settings.RETRIEVER_K_CANDIDATES
        retrieved = self.vectorstore.similarity_search(message, k=k)
        filtered = [d for d in retrieved if not self._is_future_doc(d, query_date)]
        return filtered[: settings.RETRIEVER_K]

    async def chat(
        self,
        message: str,
        history: list[HistoryTurn],
        query_date: str | None = None,
    ):
        if self.vectorstore is None:
            logger.error("Vector store not initialized")
            raise ValueError("Vector store not initialized. Please ensure documents are loaded.")

        if not settings.GROQ_API_KEY:
            logger.error("GROQ_API_KEY is missing")
            raise ValueError("GROQ_API_KEY is not configured on the server.")

        effective_query_date = resolve_query_date(message, query_date)
        logger.info("Retrieving relevant documents (query date: %s)", effective_query_date)

        try:
            retrieved = self.retrieve(message, effective_query_date)
        except Exception as e:
            logger.error(f"Error during retrieval: {e}")
            raise ValueError("Failed to retrieve relevant information from the knowledge base.")

        context_blocks: list[str] = []
        sources = []
        for doc in retrieved:
            src = doc.metadata.get("source", "unknown")
            doc_date = doc.metadata.get("doc_date", "unknown")
            doc_type_label = doc.metadata.get("doc_type_label", "unknown")
            label = Path(str(src)).name
            excerpt = (doc.page_content or "").strip()
            if len(excerpt) > 400:
                excerpt = excerpt[:400].rsplit(" ", 1)[0] + "…"

            context_blocks.append(
                f"[Source: {label}, Type: {doc_type_label}, Date: {doc_date}]\n{doc.page_content}"
            )
            sources.append({
                "source": label,
                "excerpt": excerpt,
                "date": doc_date if doc_date != "unknown" else None,
                "type": doc_type_label if doc_type_label != "unknown" else None,
            })

        context_text = "\n\n---\n\n".join(context_blocks) if context_blocks else "(no context retrieved)"

        try:
            llm = ChatGroq(
                groq_api_key=settings.GROQ_API_KEY,
                model_name=settings.GROQ_MODEL,
                temperature=0.1,
            )

            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        settings.SYSTEM_PROMPT
                        + "\n\nThe user's query date is {query_date}. "
                        "Use any relevant context below, including older documents, if they answer the question. "
                        "Documents dated after the query date are not included. "
                        "When you rely on information from a source, mention when it was recorded using that source's date. "
                        "If newer and older sources conflict, note the dates and prefer the newer one unless the question is about history. "
                        "CRITICAL: Answer ONLY using the provided context. "
                        "If the answer is not contained within the context below, state that you do not have enough information to answer. "
                        "Do not use outside knowledge.\n\nContext:\n{context}",
                    ),
                    MessagesPlaceholder("history"),
                    ("human", "{input}"),
                ]
            )

            chain = prompt | llm
            history_msgs = self.history_to_messages(history)
            result = await chain.ainvoke(
                {
                    "context": context_text,
                    "history": history_msgs,
                    "input": message,
                    "query_date": effective_query_date,
                }
            )
            answer = result.content if hasattr(result, "content") else str(result)
        except Exception as e:
            logger.error(f"Error calling Groq API: {e}")
            raise ValueError("The assistant is currently unavailable. Please try again later.")

        # Deduplicate sources by filename while preserving order
        seen = set()
        unique_sources = []
        for s in sources:
            if s["source"] not in seen:
                seen.add(s["source"])
                unique_sources.append(s)

        return str(answer), unique_sources, effective_query_date

rag_service = RAGService()
