"""Schemas for chatbot request and response."""

from pydantic import BaseModel
from typing import Optional, List


class ChatMessage(BaseModel):
    """A single chat message."""
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """Request schema for chat endpoint."""
    message: str
    conversation_history: Optional[List[ChatMessage]] = None


class ChatResponse(BaseModel):
    """Response schema for chat endpoint."""
    response: str
    action_taken: Optional[str] = None
    task_data: Optional[dict] = None
