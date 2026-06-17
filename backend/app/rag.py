import logging
from pathlib import Path
from typing import Optional

from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, TextLoader
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

        loader = DirectoryLoader(
            str(settings.DOCS_DIR),
            glob="**/*.*",
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"},
            show_progress=False,
            use_multithreading=True,
            silent_errors=True,
        )
        docs = loader.load()
        allowed_suffixes = {".md", ".txt", ".markdown"}
        filtered: list[Document] = []
        for d in docs:
            src = d.metadata.get("source", "")
            if Path(src).suffix.lower() in allowed_suffixes:
                filtered.append(d)
        return filtered

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
            label = Path(str(src)).name
            excerpt = (doc.page_content or "").strip()
            if len(excerpt) > 400:
                excerpt = excerpt[:400].rsplit(" ", 1)[0] + "…"
            context_blocks.append(f"[{label}]\n{doc.page_content}")
            sources.append({"source": label, "excerpt": excerpt})

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
