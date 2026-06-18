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

DOC_TYPE_LABELS = {"A": "announcement", "S": "slides"}


def parse_document_filename(stem: str) -> dict[str, str]:
    """
    Parse filenames:
      <A|S>_<YYYYMMDD>
      <A|S>_<YYYYMMDD>_<Number>
    A = announcement, S = slides.
    """
    unknown = {
        "doc_type": "unknown",
        "doc_type_label": "unknown",
        "doc_date": "unknown",
        "doc_number": "1",
    }
    parts = stem.split("_")
    if len(parts) < 2:
        return unknown

    kind = parts[0].upper()
    if kind not in DOC_TYPE_LABELS:
        return unknown

    date_raw = parts[1]
    if len(date_raw) != 8 or not date_raw.isdigit():
        return {**unknown, "doc_type": kind, "doc_type_label": DOC_TYPE_LABELS[kind]}

    doc_date = f"{date_raw[:4]}-{date_raw[4:6]}-{date_raw[6:8]}"
    doc_number = parts[2] if len(parts) > 2 else "1"

    return {
        "doc_type": kind,
        "doc_type_label": DOC_TYPE_LABELS[kind],
        "doc_date": doc_date,
        "doc_number": doc_number,
    }


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
                    meta = parse_document_filename(filename)
                    doc.metadata.update(meta)
                
                all_docs.extend(loaded)
            except Exception as e:
                logger.error(f"Error loading documents with {loader.__class__.__name__}: {e}")

        return all_docs

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

    async def chat(self, message: str, history: list[HistoryTurn]):
        if self.vectorstore is None:
            logger.error("Vector store not initialized")
            raise ValueError("Vector store not initialized. Please ensure documents are loaded.")

        if not settings.GROQ_API_KEY:
            logger.error("GROQ_API_KEY is missing")
            raise ValueError("GROQ_API_KEY is not configured on the server.")

        try:
            retriever = self.vectorstore.as_retriever(search_kwargs={"k": settings.RETRIEVER_K})
            retrieved = retriever.invoke(message)
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
                    ("system", settings.SYSTEM_PROMPT + "\n\nCRITICAL: Answer ONLY using the provided context. If the answer is not contained within the context below, state that you do not have enough information to answer. Do not use outside knowledge.\n\nContext:\n{context}"),
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

        return str(answer), unique_sources

rag_service = RAGService()
