from pydantic_settings import BaseSettings
import os
from pathlib import Path

class Settings(BaseSettings):
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    
    DOCS_DIR: Path = Path(__file__).resolve().parent.parent / "docs"
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 120
    RETRIEVER_K: int = 4
    
    SYSTEM_PROMPT: str = """You are Practi, a helpful assistant for practicum and internship students. \
Answer only using the provided context. If the answer is not in the context, say so politely."""

    def get_cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

settings = Settings()
