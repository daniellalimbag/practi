import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@patch("app.main.get_llm_config", new_callable=AsyncMock)
def test_llm_config_endpoint(mock_get_llm_config):
    mock_get_llm_config.return_value = {
        "default_provider": "groq",
        "groq_model": "llama-3.1-8b-instant",
        "groq_available": True,
        "default_ollama_model": "llama3.1:8b",
        "ollama_base_url": "http://localhost:11434",
        "ollama_available": True,
        "ollama_models": ["llama3.1:8b", "mistral:7b"],
    }

    response = client.get("/api/llm/config")
    assert response.status_code == 200
    data = response.json()
    assert data["default_provider"] == "groq"
    assert data["ollama_models"] == ["llama3.1:8b", "mistral:7b"]
