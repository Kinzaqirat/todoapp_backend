from typing import Optional
from pydantic import BaseModel, Field
from ..models import Priority # Import Priority from models.py

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    # user_id will be derived from auth, not part of create payload

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    is_completed: Optional[bool] = None
    priority: Optional[Priority] = None
    tags: Optional[list[str]] = None
    due_date: Optional[str] = None # Will need parsing in the endpoint
    recurrence: Optional[str] = None
