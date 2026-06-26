import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.schemas import ChatRequest, ChatResponse, LlmConfigResponse
from app.rag import rag_service
from app.llm import get_llm_config

logging.basicConfig(level=logging.INFO)
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load persisted vector store or build if missing
    rag_service.load_vectorstore()
    yield
    # Shutdown (nothing to clean up for in-memory Chroma)

app = FastAPI(title="practi API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/llm/config", response_model=LlmConfigResponse)
async def llm_config():
    return await get_llm_config()


@app.post("/api/chat", response_model=ChatResponse)
async def chat(body: ChatRequest):
    try:
        answer, sources, effective_query_date, provider, model = await rag_service.chat(
            body.message,
            body.history,
            body.query_date,
            body.llm_provider,
            body.ollama_model,
        )
        return ChatResponse(
            answer=answer,
            sources=sources,
            query_date=effective_query_date,
            llm_provider=provider,
            model=model,
        )
    except ValueError as e:
        # These are expected errors we handle (missing key, not initialized, etc.)
        error_msg = str(e)
        if "GROQ_API_KEY" in error_msg or "LLM_PROVIDER" in error_msg:
            raise HTTPException(status_code=500, detail=error_msg)
        raise HTTPException(status_code=503, detail=error_msg)
    except Exception as e:
        # Unexpected errors
        logger.error(f"Unhandled error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred. Please try again later.")
