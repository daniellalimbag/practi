import logging
from collections import Counter
from pathlib import Path

from langchain_community.document_loaders import (
    Docx2txtLoader,
    DirectoryLoader,
    PyMuPDFLoader,
    PyPDFLoader,
    TextLoader,
    UnstructuredPowerPointLoader,
)
from langchain_core.documents import Document

from app.config import settings
from app.doc_metadata import parse_document_filename
from app.text_utils import normalize_extracted_text

logger = logging.getLogger(__name__)


def _tag_metadata(docs: list[Document]) -> list[Document]:
    for doc in docs:
        src = doc.metadata.get("source", "")
        filename = Path(str(src)).stem
        doc.metadata.update(parse_document_filename(filename))
    return docs


def load_pdf_documents() -> list[Document]:
    docs: list[Document] = []
    for pdf_path in sorted(settings.DOCS_DIR.glob("**/*.pdf")):
        loaded: list[Document] = []
        try:
            loaded = PyMuPDFLoader(str(pdf_path)).load()
            loader_name = "PyMuPDFLoader"
        except Exception as exc:
            logger.warning("PyMuPDF failed for %s (%s); falling back to PyPDFLoader", pdf_path.name, exc)
            try:
                loaded = PyPDFLoader(str(pdf_path)).load()
                loader_name = "PyPDFLoader"
            except Exception as fallback_exc:
                logger.error("Failed to load PDF %s: %s", pdf_path.name, fallback_exc)
                continue

        for doc in loaded:
            doc.page_content = normalize_extracted_text(doc.page_content or "")

        loaded = [d for d in loaded if (d.page_content or "").strip()]
        _tag_metadata(loaded)
        chars = sum(len(d.page_content) for d in loaded)
        logger.info(
            "Loaded PDF %s via %s: %s pages, %s chars",
            pdf_path.name,
            loader_name,
            len(loaded),
            chars,
        )
        docs.extend(loaded)
    return docs


def load_all_documents() -> list[Document]:
    if not settings.DOCS_DIR.is_dir():
        logger.warning("Docs directory missing at %s", settings.DOCS_DIR)
        return []

    all_docs: list[Document] = []
    loaders = [
        ("text", DirectoryLoader(str(settings.DOCS_DIR), glob="**/*.txt", loader_cls=TextLoader, loader_kwargs={"encoding": "utf-8"})),
        ("markdown", DirectoryLoader(str(settings.DOCS_DIR), glob="**/*.md", loader_cls=TextLoader, loader_kwargs={"encoding": "utf-8"})),
        ("docx", DirectoryLoader(str(settings.DOCS_DIR), glob="**/*.docx", loader_cls=Docx2txtLoader)),
        ("pptx", DirectoryLoader(str(settings.DOCS_DIR), glob="**/*.pptx", loader_cls=UnstructuredPowerPointLoader)),
    ]

    for label, loader in loaders:
        try:
            loaded = loader.load()
            _tag_metadata(loaded)
            all_docs.extend(loaded)
            logger.info("Loaded %s %s file(s) via %s", len(loaded), label, loader.__class__.__name__)
        except Exception as exc:
            logger.error("Error loading %s documents: %s", label, exc)

    all_docs.extend(load_pdf_documents())
    return all_docs


def log_chunk_summary(splits: list[Document]) -> None:
    by_source = Counter(Path(str(d.metadata.get("source", "unknown"))).name for d in splits)
    logger.info("Ingested %s chunks from %s source files", len(splits), len(by_source))
    for name, count in by_source.most_common(15):
        logger.info("  %4d chunks  %s", count, name)
    if len(by_source) > 15:
        logger.info("  ... and %s more files", len(by_source) - 15)
