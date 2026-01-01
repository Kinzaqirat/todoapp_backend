"""Event schemas for Kafka topics."""

from datetime import datetime
from pydantic import BaseModel
from uuid import UUID


class TaskEvent(BaseModel):
    """Event published to task-events topic.

    Attributes:
        event_type: Operation type (task.created, task.updated, task.completed, task.deleted)
        task_id: Related task ID
        task_data: Serialized Task object
        user_id: Who performed the action
        timestamp: When event occurred
    """
    event_type: str
    task_id: int
    task_data: dict
    user_id: UUID
    timestamp: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "task.created",
                "task_id": 42,
                "task_data": {
                    "title": "Buy groceries",
                    "status": "pending",
                    "priority": "medium"
                },
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2025-12-29T14:30:00Z"
            }
        }


class ReminderEvent(BaseModel):
    """Event published to reminders topic.

    Attributes:
        task_id: Related task ID
        title: Task title
        due_at: When task is due
        remind_at: When to send reminder
        user_id: Task owner
    """
    task_id: int
    title: str
    due_at: datetime
    remind_at: datetime
    user_id: UUID

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": 42,
                "title": "Buy groceries",
                "due_at": "2025-12-30T10:00:00Z",
                "remind_at": "2025-12-30T09:30:00Z",
                "user_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class SyncEvent(BaseModel):
    """Event published to task-updates topic for real-time sync.

    Attributes:
        event_type: Sync event type
        task_id: Related task ID
        task_data: Serialized Task object
        user_id: Task owner
        timestamp: When event occurred
    """
    event_type: str = "sync.task_changed"
    task_id: int
    task_data: dict
    user_id: UUID
    timestamp: datetime
