import logging
import shutil
import sys
from pathlib import Path

# Add the current directory to sys.path to allow importing from 'app'
sys.path.append(str(Path(__file__).resolve().parent))

from app.rag import rag_service
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting document ingestion...")
    
    if not settings.DOCS_DIR.exists():
        logger.error(f"Docs directory not found at {settings.DOCS_DIR}")
        sys.exit(1)

    if settings.CHROMA_DB_DIR.exists():
        logger.info("Removing existing Chroma DB at %s", settings.CHROMA_DB_DIR)
        shutil.rmtree(settings.CHROMA_DB_DIR)

    # Build and persist the vector store
    rag_service.build_vectorstore(persist=True)
    
    logger.info("Ingestion complete. Chroma DB persisted to disk.")

if __name__ == "__main__":
    main()
