"""Data models for the Task Manager API."""

from datetime import datetime
from typing import Optional, List
from enum import Enum
from sqlmodel import Field, SQLModel, Relationship, Column, JSON


class Priority(str, Enum):
    """Priority levels for tasks."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class User(SQLModel, table=True):
    __tablename__ = "user"  # Explicitly set table name
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    tasks: List["Task"] = Relationship(back_populates="owner")


class Task(SQLModel, table=True):
    """Represents a single task in the task manager.
    
    Attributes:
        id: Unique identifier for the task
        user_id: Foreign key to User
        title: Task title (required)
        description: Optional detailed description
        completed: Whether the task is completed
        priority: Priority level (high, medium, low)
        tags: List of tags for categorization
        due_date: Optional due date and time
        recurrence: Recurrence pattern (daily, weekly, monthly)
        created_at: Timestamp when task was created
        updated_at: Timestamp when task was last updated
    """
    __tablename__ = "task"  # Explicitly set table name
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")  # Changed to match User table name
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    completed: bool = False
    priority: Optional[Priority] = None
    tags: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    due_date: Optional[datetime] = None
    recurrence: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    owner: User = Relationship(back_populates="tasks")  # This matches User.tasks now