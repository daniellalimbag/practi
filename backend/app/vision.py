"""Vision-model text extraction from document images at ingest time."""

from __future__ import annotations

import base64
import hashlib
import logging

from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama

from app.config import settings

logger = logging.getLogger(__name__)

_NO_CONTENT = "NO_CONTENT"
_CACHE: dict[str, str] = {}

VISION_PROMPT = """You are extracting knowledge for a searchable internship/practicum database.
Source: {context}

Extract ALL readable text from this image verbatim.
Also describe diagrams, tables, screenshots, forms, and step-by-step instructions clearly.
Use plain text only. Be thorough and factual.
If the image has no useful information, reply with exactly: NO_CONTENT"""


def resolve_vision_provider() -> str:
    return settings.VISION_PROVIDER.lower()


def get_vision_model():
    provider = resolve_vision_provider()

    if provider == "groq":
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is required for vision ingest with Groq.")
        return ChatGroq(
            groq_api_key=settings.GROQ_API_KEY,
            model_name=settings.GROQ_VISION_MODEL,
            temperature=0.0,
        )

    if provider == "ollama":
        return ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_VISION_MODEL,
            temperature=0.0,
        )

    raise ValueError(f"Unsupported VISION_PROVIDER: {provider}. Use 'groq' or 'ollama'.")


def _cache_key(image_bytes: bytes, context: str) -> str:
    return hashlib.sha256(image_bytes + context.encode("utf-8")).hexdigest()


def describe_image(image_bytes: bytes, mime_type: str, *, context: str) -> str:
    """Return extracted text/description for an image, or empty string on failure."""
    if not settings.ENABLE_VISION_INGEST:
        return ""

    if len(image_bytes) < settings.VISION_MIN_IMAGE_BYTES:
        return ""

    key = _cache_key(image_bytes, context)
    if key in _CACHE:
        return _CACHE[key]

    b64 = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime_type};base64,{b64}"
    prompt = VISION_PROMPT.format(context=context)

    try:
        model = get_vision_model()
        result = model.invoke(
            [
                HumanMessage(
                    content=[
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ]
                )
            ]
        )
        text = (result.content if hasattr(result, "content") else str(result)).strip()
    except Exception as exc:
        logger.warning("Vision extract failed for %s: %s", context, exc)
        _CACHE[key] = ""
        return ""

    if not text or text.upper() == _NO_CONTENT:
        _CACHE[key] = ""
        return ""

    _CACHE[key] = text
    logger.info("Vision extracted %s chars from %s", len(text), context)
    return text


def clear_vision_cache() -> None:
    _CACHE.clear()


def build_vision_appendix(images, describe_fn=describe_image) -> str:
    """Run vision on a list of ExtractedImage objects and join results."""
    blocks: list[str] = []
    for image in images:
        extracted = describe_fn(image.image_bytes, image.mime_type, context=image.label)
        if extracted:
            blocks.append(f"[{image.label}]\n{extracted}")
    if not blocks:
        return ""
    return "\n\n[Vision extract]\n" + "\n\n".join(blocks)
