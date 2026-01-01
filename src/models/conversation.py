from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import JSON
from uuid import UUID

class Message(SQLModel):
    role: str
    content: str
    timestamp: datetime

class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    messages: List[dict] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
