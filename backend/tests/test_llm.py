import pytest
from unittest.mock import patch, MagicMock
from app.llm import get_chat_model
from app.config import settings

def test_get_chat_model_groq_success():
    with patch.object(settings, "LLM_PROVIDER", "groq"), \
         patch.object(settings, "GROQ_API_KEY", "test_key"):
        model = get_chat_model()
        from langchain_groq import ChatGroq
        assert isinstance(model, ChatGroq)
        assert model.groq_api_key.get_secret_value() == "test_key"

def test_get_chat_model_groq_no_key():
    with patch.object(settings, "LLM_PROVIDER", "groq"), \
         patch.object(settings, "GROQ_API_KEY", ""):
        with pytest.raises(ValueError, match="GROQ_API_KEY is not configured"):
            get_chat_model()

def test_get_chat_model_ollama_success():
    with patch.object(settings, "LLM_PROVIDER", "ollama"), \
         patch.object(settings, "OLLAMA_MODEL", "test_model"), \
         patch.object(settings, "OLLAMA_BASE_URL", "http://test:11434"):
        model = get_chat_model()
        from langchain_ollama import ChatOllama
        assert isinstance(model, ChatOllama)
        assert model.model == "test_model"
        assert str(model.base_url).rstrip("/") == "http://test:11434"

def test_get_chat_model_ollama_override():
    with patch.object(settings, "LLM_PROVIDER", "groq"), \
         patch.object(settings, "OLLAMA_MODEL", "default_model"), \
         patch.object(settings, "OLLAMA_BASE_URL", "http://test:11434"):
        model = get_chat_model(provider="ollama", ollama_model="custom:7b")
        from langchain_ollama import ChatOllama
        assert isinstance(model, ChatOllama)
        assert model.model == "custom:7b"


def test_get_chat_model_unsupported():
    with patch.object(settings, "LLM_PROVIDER", "invalid"):
        with pytest.raises(ValueError, match="Unsupported LLM_PROVIDER"):
            get_chat_model()


def test_get_active_model_name_ollama():
    with patch.object(settings, "LLM_PROVIDER", "groq"), \
         patch.object(settings, "OLLAMA_MODEL", "llama3.1:8b"), \
         patch.object(settings, "GROQ_MODEL", "llama-3.1-8b-instant"):
        from app.llm import get_active_model_name
        assert get_active_model_name("ollama", "mistral:7b") == "mistral:7b"
        assert get_active_model_name("groq") == "llama-3.1-8b-instant"
