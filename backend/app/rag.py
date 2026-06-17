import logging
from pathlib import Path
from typing import Optional

from langchain_chroma import Chroma
from langchain_community.document_loaders import (
    DirectoryLoader,
    TextLoader,
    PyPDFLoader,
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
        if not settings.DOCS_DIR.is_dir():
            logger.warning("Docs directory missing at %s — using empty corpus", settings.DOCS_DIR)
            return []

        all_docs = []
        
        # Define loaders for different file types
        loaders = [
            DirectoryLoader(str(settings.DOCS_DIR), glob="**/*.txt", loader_cls=TextLoader, loader_kwargs={"encoding": "utf-8"}),
            DirectoryLoader(str(settings.DOCS_DIR), glob="**/*.md", loader_cls=TextLoader, loader_kwargs={"encoding": "utf-8"}),
            DirectoryLoader(str(settings.DOCS_DIR), glob="**/*.pdf", loader_cls=PyPDFLoader),
            DirectoryLoader(str(settings.DOCS_DIR), glob="**/*.docx", loader_cls=Docx2txtLoader),
            DirectoryLoader(str(settings.DOCS_DIR), glob="**/*.pptx", loader_cls=UnstructuredPowerPointLoader),
        ]

        for loader in loaders:
            try:
                loaded = loader.load()
                # Post-process metadata to extract date and number from filename
                for doc in loaded:
                    src = doc.metadata.get("source", "")
                    filename = Path(str(src)).stem
                    # Naming convention: <Date>_<Number>
                    if "_" in filename:
                        parts = filename.split("_")
                        doc.metadata["doc_date"] = parts[0]
                        doc.metadata["doc_number"] = parts[1]
                    else:
                        doc.metadata["doc_date"] = "unknown"
                        doc.metadata["doc_number"] = "0"
                
                all_docs.extend(loaded)
            except Exception as e:
                logger.error(f"Error loading documents with {loader.__class__.__name__}: {e}")

        return all_docs

    def build_vectorstore(self):
        raw_docs = self.load_documents()
        if not raw_docs:
            logger.warning("No documents loaded from %s", settings.DOCS_DIR)

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            add_start_index=True,
        )
        splits = splitter.split_documents(raw_docs)

        self.vectorstore = Chroma.from_documents(
            documents=splits,
            embedding=self.embeddings,
            collection_name="practi_kb",
            persist_directory=None,
        )
        logger.info("Chroma index built with %s chunks from %s files", len(splits), len(raw_docs))

    def history_to_messages(self, history: list[HistoryTurn]) -> list[BaseMessage]:
        out: list[BaseMessage] = []
        for turn in history:
            if turn.role == "user":
                out.append(HumanMessage(content=turn.content))
            else:
                out.append(AIMessage(content=turn.content))
        return out

    async def chat(self, message: str, history: list[HistoryTurn]):
        if self.vectorstore is None:
            raise ValueError("Vector store not initialized")

        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not configured")

        retriever = self.vectorstore.as_retriever(search_kwargs={"k": settings.RETRIEVER_K})
        retrieved = retriever.invoke(message)

        context_blocks: list[str] = []
        sources = []
        for doc in retrieved:
            src = doc.metadata.get("source", "unknown")
            doc_date = doc.metadata.get("doc_date", "unknown")
            label = Path(str(src)).name
            excerpt = (doc.page_content or "").strip()
            if len(excerpt) > 400:
                excerpt = excerpt[:400].rsplit(" ", 1)[0] + "…"
            
            context_blocks.append(f"[Source: {label}, Date: {doc_date}]\n{doc.page_content}")
            sources.append({
                "source": label,
                "excerpt": excerpt,
                "date": doc_date if doc_date != "unknown" else None
            })

        context_text = "\n\n---\n\n".join(context_blocks) if context_blocks else "(no context retrieved)"

        llm = ChatGroq(
            groq_api_key=settings.GROQ_API_KEY,
            model_name="llama3-8b-8192",
            temperature=0.2,
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", settings.SYSTEM_PROMPT + "\n\nContext:\n{context}"),
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
            }
        )
        answer = result.content if hasattr(result, "content") else str(result)

        seen = set()
        unique_sources = []
        for s in sources:
            if s["source"] not in seen:
                seen.add(s["source"])
                unique_sources.append(s)

        return str(answer), unique_sources

rag_service = RAGService()
