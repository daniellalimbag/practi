from pathlib import Path
import os

from pydantic_settings import BaseSettings, SettingsConfigDict

# Disable Chroma anonymized telemetry before chromadb is imported elsewhere.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    
    LLM_PROVIDER: str = "groq"  # "groq" or "ollama"
    LLM_TEMPERATURE: float = 0.1
    
    OLLAMA_MODEL: str = "llama3.1:8b"
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    DOCS_DIR: Path = Path(__file__).resolve().parent.parent / "docs"
    CHROMA_DB_DIR: Path = Path(__file__).resolve().parent.parent / "chroma_db"
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 150
    RETRIEVER_K: int = 8
    RETRIEVER_K_CANDIDATES: int = 24

    ENABLE_VISION_INGEST: bool = True
    VISION_PROVIDER: str = "ollama"  # "groq" or "ollama"
    GROQ_VISION_MODEL: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    OLLAMA_VISION_MODEL: str = "llama3.2-vision"
    VISION_MIN_TEXT_CHARS: int = 80
    VISION_MIN_IMAGE_BYTES: int = 4096
    VISION_MAX_IMAGES_PER_FILE: int = 30
    VISION_RENDER_DPI: int = 150

    SYSTEM_PROMPT: str = """You are Practi, a helpful assistant for practicum and internship students. \
Answer only using the provided context. If the answer is not in the context, say so politely."""

    def get_cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
