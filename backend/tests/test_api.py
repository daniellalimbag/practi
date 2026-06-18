import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app
from app.rag import rag_service

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_chat_validation_error():
    # Empty message
    response = client.post("/api/chat", json={"message": "", "history": []})
    assert response.status_code == 422

    # Missing message
    response = client.post("/api/chat", json={"history": []})
    assert response.status_code == 422

    # Invalid role in history
    response = client.post("/api/chat", json={
        "message": "hello",
        "history": [{"role": "invalid", "content": "hi"}]
    })
    assert response.status_code == 422

@patch("app.rag.rag_service.chat")
def test_chat_success(mock_chat):
    # Mock the RAG service response
    mock_chat.return_value = (
        "This is a mock answer",
        [{"source": "test.pdf", "excerpt": "test excerpt", "date": "2024-01-01"}],
        "2024-01-01",
    )
    
    response = client.post("/api/chat", json={
        "message": "What is the policy?",
        "history": []
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "This is a mock answer"
    assert len(data["sources"]) == 1
    assert data["sources"][0]["source"] == "test.pdf"
    assert data["query_date"] == "2024-01-01"

@patch("app.rag.rag_service.chat")
def test_chat_groq_key_missing(mock_chat):
    # Simulate a ValueError for missing API key
    mock_chat.side_effect = ValueError("GROQ_API_KEY is not configured on the server.")
    
    response = client.post("/api/chat", json={
        "message": "hello",
        "history": []
    })
    
    assert response.status_code == 500
    assert "GROQ_API_KEY" in response.json()["detail"]

@patch("app.rag.rag_service.chat")
def test_chat_vectorstore_not_initialized(mock_chat):
    # Simulate a ValueError for vector store not ready
    mock_chat.side_effect = ValueError("Vector store not initialized. Please ensure documents are loaded.")
    
    response = client.post("/api/chat", json={
        "message": "hello",
        "history": []
    })
    
    assert response.status_code == 503
    assert "Vector store not initialized" in response.json()["detail"]
