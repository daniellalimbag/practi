import logging

import httpx
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama

from app.config import settings

logger = logging.getLogger(__name__)


def resolve_provider(provider: str | None = None) -> str:
    return (provider or settings.LLM_PROVIDER).lower()


def resolve_ollama_model(model: str | None = None) -> str:
    return (model or settings.OLLAMA_MODEL).strip()


def resolve_groq_model(model: str | None = None) -> str:
    return (model or settings.GROQ_MODEL).strip()


def get_chat_model(
    provider: str | None = None,
    ollama_model: str | None = None,
    groq_model: str | None = None,
):
    """Return the configured chat model, with optional per-request overrides."""
    resolved_provider = resolve_provider(provider)

    if resolved_provider == "groq":
        if not settings.GROQ_API_KEY:
            logger.error("GROQ_API_KEY is missing")
            raise ValueError("GROQ_API_KEY is not configured on the server.")

        model_name = resolve_groq_model(groq_model)
        logger.info("Using Groq provider with model %s", model_name)
        return ChatGroq(
            groq_api_key=settings.GROQ_API_KEY,
            model_name=model_name,
            temperature=settings.LLM_TEMPERATURE,
        )

    if resolved_provider == "ollama":
        model_name = resolve_ollama_model(ollama_model)
        logger.info(
            "Using Ollama provider at %s with model %s",
            settings.OLLAMA_BASE_URL,
            model_name,
        )
        return ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=model_name,
            temperature=settings.LLM_TEMPERATURE,
        )

    logger.error("Unsupported LLM_PROVIDER: %s", resolved_provider)
    raise ValueError(
        f"Unsupported LLM_PROVIDER: {resolved_provider}. Use 'groq' or 'ollama'."
    )


def get_active_model_name(
    provider: str | None = None,
    ollama_model: str | None = None,
    groq_model: str | None = None,
) -> str:
    resolved_provider = resolve_provider(provider)
    if resolved_provider == "ollama":
        return resolve_ollama_model(ollama_model)
    return resolve_groq_model(groq_model)


async def list_ollama_models() -> list[str]:
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        logger.warning("Could not list Ollama models from %s: %s", url, exc)
        return []

    models = []
    for item in payload.get("models", []):
        name = item.get("name")
        if name:
            models.append(name)
    return sorted(models)


async def get_llm_config() -> dict:
    ollama_models = await list_ollama_models()
    default_ollama = settings.OLLAMA_MODEL
    if default_ollama not in ollama_models and ollama_models:
        default_ollama = ollama_models[0]

    return {
        "default_provider": settings.LLM_PROVIDER.lower(),
        "groq_model": settings.GROQ_MODEL,
        "groq_available": bool(settings.GROQ_API_KEY),
        "default_ollama_model": default_ollama,
        "ollama_base_url": settings.OLLAMA_BASE_URL,
        "ollama_available": bool(ollama_models),
        "ollama_models": ollama_models,
    }
