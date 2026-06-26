from typing import Literal, Optional
from pydantic import BaseModel, Field

class HistoryTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1)

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: list[HistoryTurn] = Field(default_factory=list)
    query_date: Optional[str] = Field(
        default=None,
        description="Reference date for retrieval (YYYY-MM-DD). Defaults to today.",
    )
    llm_provider: Optional[Literal["groq", "ollama"]] = Field(
        default=None,
        description="Override server LLM provider for this request.",
    )
    ollama_model: Optional[str] = Field(
        default=None,
        description="Ollama model name when llm_provider is ollama.",
    )


class LlmConfigResponse(BaseModel):
    default_provider: str
    groq_model: str
    groq_available: bool
    default_ollama_model: str
    ollama_base_url: str
    ollama_available: bool
    ollama_models: list[str]

class SourceItem(BaseModel):
    source: str
    excerpt: str
    date: Optional[str] = None
    type: Optional[str] = None  # "announcement" or "slides"

class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
    query_date: str
    llm_provider: str
    model: str
