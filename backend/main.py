from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DOCS_DIR = Path(__file__).resolve().parent / "docs"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
RETRIEVER_K = 4

SYSTEM_PROMPT = """You are Practi, a helpful assistant for practicum and internship students. \
Answer only using the provided context. If the answer is not in the context, say so politely."""

vectorstore: Chroma | None = None
embeddings: HuggingFaceEmbeddings | None = None


def _load_documents() -> list[Document]:
    if not DOCS_DIR.is_dir():
        logger.warning("Docs directory missing at %s — using empty corpus", DOCS_DIR)
        return []

    loader = DirectoryLoader(
        str(DOCS_DIR),
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


def _build_vectorstore() -> Chroma:
    global embeddings
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    raw_docs = _load_documents()
    if not raw_docs:
        logger.warning("No documents loaded from %s", DOCS_DIR)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        add_start_index=True,
    )
    splits = splitter.split_documents(raw_docs)

    vs = Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        collection_name="practi_kb",
        persist_directory=None,
    )
    logger.info("Chroma index built with %s chunks from %s files", len(splits), len(raw_docs))
    return vs


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "").strip()
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


app = FastAPI(title="practi API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    global vectorstore
    vectorstore = _build_vectorstore()


class HistoryTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: list[HistoryTurn] = Field(default_factory=list)


class SourceItem(BaseModel):
    source: str
    excerpt: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceItem]


def _history_to_messages(history: list[HistoryTurn]) -> list[BaseMessage]:
    out: list[BaseMessage] = []
    for turn in history:
        if turn.role == "user":
            out.append(HumanMessage(content=turn.content))
        else:
            out.append(AIMessage(content=turn.content))
    return out


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest) -> ChatResponse:
    if vectorstore is None:
        raise HTTPException(status_code=503, detail="Vector store not initialized")

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured")

    retriever = vectorstore.as_retriever(search_kwargs={"k": RETRIEVER_K})
    retrieved = retriever.invoke(body.message)

    context_blocks: list[str] = []
    sources: list[SourceItem] = []
    for doc in retrieved:
        src = doc.metadata.get("source", "unknown")
        label = Path(str(src)).name
        excerpt = (doc.page_content or "").strip()
        if len(excerpt) > 400:
            excerpt = excerpt[:400].rsplit(" ", 1)[0] + "…"
        context_blocks.append(f"[{label}]\n{doc.page_content}")
        sources.append(SourceItem(source=label, excerpt=excerpt))

    context_text = "\n\n---\n\n".join(context_blocks) if context_blocks else "(no context retrieved)"

    llm = ChatGroq(
        groq_api_key=api_key,
        model_name="llama3-8b-8192",
        temperature=0.2,
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT + "\n\nContext:\n{context}"),
            MessagesPlaceholder("history"),
            ("human", "{input}"),
        ]
    )

    chain = prompt | llm
    history_msgs = _history_to_messages(body.history)
    result = chain.invoke(
        {
            "context": context_text,
            "history": history_msgs,
            "input": body.message,
        }
    )
    answer = result.content if hasattr(result, "content") else str(result)

    seen: set[str] = set()
    unique_sources: list[SourceItem] = []
    for s in sources:
        if s.source not in seen:
            seen.add(s.source)
            unique_sources.append(s)

    return ChatResponse(answer=str(answer), sources=unique_sources)
