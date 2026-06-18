from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    DOCS_DIR: Path = Path(__file__).resolve().parent.parent / "docs"
    CHROMA_DB_DIR: Path = Path(__file__).resolve().parent.parent / "chroma_db"
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 150
    RETRIEVER_K: int = 8
    RETRIEVER_K_CANDIDATES: int = 24

    SYSTEM_PROMPT: str = """You are Practi, a helpful assistant for practicum and internship students. \
Answer only using the provided context. If the answer is not in the context, say so politely."""

    def get_cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
