import logging
from collections import Counter
from pathlib import Path

import fitz
from langchain_community.document_loaders import (
    Docx2txtLoader,
    DirectoryLoader,
    PyPDFLoader,
    TextLoader,
    UnstructuredPowerPointLoader,
)
from langchain_core.documents import Document

from app.config import settings
from app.doc_metadata import parse_document_filename
from app.image_extract import (
    extract_docx_images,
    extract_pdf_page_images,
    extract_pptx_images,
)
from app.text_utils import normalize_extracted_text
from app.vision import build_vision_appendix, clear_vision_cache

logger = logging.getLogger(__name__)


def _tag_metadata(docs: list[Document]) -> list[Document]:
    for doc in docs:
        src = doc.metadata.get("source", "")
        filename = Path(str(src)).stem
        doc.metadata.update(parse_document_filename(filename))
    return docs


def _append_vision_text(base_text: str, appendix: str) -> str:
    base = (base_text or "").strip()
    appendix = (appendix or "").strip()
    if not appendix:
        return base
    if not base:
        return appendix
    return f"{base}\n\n{appendix}"


def _enrich_pdf_page(doc: Document, pdf_path: Path, page_num: int, page, pdf: fitz.Document) -> Document:
    if not settings.ENABLE_VISION_INGEST:
        return doc
    images = extract_pdf_page_images(pdf_path, page_num, page, pdf)
    appendix = build_vision_appendix(images)
    doc.page_content = _append_vision_text(doc.page_content, appendix)
    if appendix:
        doc.metadata["vision_enriched"] = True
    return doc


def _load_pdf_with_pymupdf(pdf_path: Path) -> list[Document]:
    docs: list[Document] = []
    try:
        pdf = fitz.open(pdf_path)
    except Exception as exc:
        logger.warning("PyMuPDF open failed for %s (%s); falling back to PyPDFLoader", pdf_path.name, exc)
        try:
            loaded = PyPDFLoader(str(pdf_path)).load()
            _tag_metadata(loaded)
            return loaded
        except Exception as fallback_exc:
            logger.error("Failed to load PDF %s: %s", pdf_path.name, fallback_exc)
            return []

    try:
        for page_num, page in enumerate(pdf, start=1):
            text = normalize_extracted_text(page.get_text() or "")
            doc = Document(
                page_content=text,
                metadata={"source": str(pdf_path), "page": page_num - 1},
            )
            doc = _enrich_pdf_page(doc, pdf_path, page_num, page, pdf)
            if (doc.page_content or "").strip():
                docs.append(doc)
    finally:
        pdf.close()

    _tag_metadata(docs)
    return docs


def load_pdf_documents() -> list[Document]:
    docs: list[Document] = []
    for pdf_path in sorted(settings.DOCS_DIR.glob("**/*.pdf")):
        loaded = _load_pdf_with_pymupdf(pdf_path)
        chars = sum(len(d.page_content) for d in loaded)
        logger.info(
            "Loaded PDF %s: %s pages, %s chars%s",
            pdf_path.name,
            len(loaded),
            chars,
            " (vision)" if settings.ENABLE_VISION_INGEST else "",
        )
        docs.extend(loaded)
    return docs


def _enrich_loaded_docs(docs: list[Document], suffix: str) -> list[Document]:
    if not settings.ENABLE_VISION_INGEST:
        return docs

    by_source: dict[str, list[Document]] = {}
    for doc in docs:
        source = str(doc.metadata.get("source", ""))
        by_source.setdefault(source, []).append(doc)

    for source, group in by_source.items():
        if not source.lower().endswith(suffix):
            continue
        appendix = build_vision_appendix(
            extract_docx_images(Path(source))
            if suffix == ".docx"
            else extract_pptx_images(Path(source))
        )
        if not appendix:
            continue
        for doc in group:
            doc.page_content = _append_vision_text(doc.page_content, appendix)
            doc.metadata["vision_enriched"] = True

    return docs


def load_all_documents() -> list[Document]:
    if not settings.DOCS_DIR.is_dir():
        logger.warning("Docs directory missing at %s", settings.DOCS_DIR)
        return []

    if settings.ENABLE_VISION_INGEST:
        clear_vision_cache()
        logger.info(
            "Vision ingest enabled via %s",
            settings.VISION_PROVIDER,
        )

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
            if label == "docx":
                loaded = _enrich_loaded_docs(loaded, ".docx")
            elif label == "pptx":
                loaded = _enrich_loaded_docs(loaded, ".pptx")
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
