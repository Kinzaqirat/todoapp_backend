from datetime import datetime
from typing import Optional
from enum import Enum
from sqlmodel import Field, SQLModel
from pydantic import field_validator

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELETED = "deleted"

class TaskPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class Task(SQLModel, table=True):
    __tablename__ = "tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=500)
    description: str = Field(default="", max_length=2000)
    status: str = Field(default="pending", max_length=20)
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    tags: str = Field(default="[]")
    completed: bool = Field(default=False)
    due_date: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)

    @field_validator("priority", mode="before")
    @classmethod
    def parse_priority(cls, v):
        if isinstance(v, str):
            try:
                return TaskPriority(v.lower())
            except ValueError:
                return TaskPriority.MEDIUM
        return v
