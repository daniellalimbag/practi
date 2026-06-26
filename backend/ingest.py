import logging
import shutil
import sys
import time
from pathlib import Path

# Add the current directory to sys.path to allow importing from 'app'
sys.path.append(str(Path(__file__).resolve().parent))

from app.rag import rag_service
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def remove_chroma_db(max_attempts: int = 5, delay_sec: float = 1.0) -> None:
    """Remove persisted Chroma data. Retries when SQLite is locked (e.g. backend running)."""
    path = settings.CHROMA_DB_DIR
    if not path.exists():
        return

    logger.info("Removing existing Chroma DB at %s", path)
    for attempt in range(1, max_attempts + 1):
        try:
            shutil.rmtree(path)
            return
        except PermissionError:
            if attempt == max_attempts:
                logger.error(
                    "Cannot remove %s — the database is in use by another process. "
                    "Stop the backend server (Ctrl+C on uvicorn), then run: python ingest.py",
                    path,
                )
                sys.exit(1)
            logger.warning(
                "Chroma DB is locked (attempt %s/%s). Retrying in %ss...",
                attempt,
                max_attempts,
                delay_sec,
            )
            time.sleep(delay_sec)


def main():
    logger.info("Starting document ingestion...")
    
    if not settings.DOCS_DIR.exists():
        logger.error(f"Docs directory not found at {settings.DOCS_DIR}")
        sys.exit(1)

    remove_chroma_db()

    # Build and persist the vector store
    rag_service.build_vectorstore(persist=True)
    
    logger.info("Ingestion complete. Chroma DB persisted to disk.")

if __name__ == "__main__":
    main()
