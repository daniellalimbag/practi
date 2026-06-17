from typing import Literal, Optional
from pydantic import BaseModel, Field

class HistoryTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1)

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: list[HistoryTurn] = Field(default_factory=list)

class SourceItem(BaseModel):
    source: str
    excerpt: str
    date: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
