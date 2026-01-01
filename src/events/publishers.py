"""Event publishers using Dapr pub/sub."""

from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum
import logging

from ..services.dapr_client import get_dapr_client, DaprTopic

logger = logging.getLogger(__name__)


class TaskEventType(str, Enum):
    """Task event types."""
    CREATED = "task.created"
    UPDATED = "task.updated"
    DELETED = "task.deleted"
    COMPLETED = "task.completed"
    UNCOMPLETED = "task.uncompleted"


class ReminderEventType(str, Enum):
    """Reminder event types."""
    SCHEDULED = "reminder.scheduled"
    TRIGGERED = "reminder.triggered"
    CANCELLED = "reminder.cancelled"


async def publish_task_created(
    task_id: int,
    task_data: Dict[str, Any],
    user_id: str = "anonymous"
) -> bool:
    """Publish task created event.

    Args:
        task_id: The created task ID
        task_data: The task data
        user_id: The user who created the task

    Returns:
        True if published successfully
    """
    client = get_dapr_client()
    return await client.publish_task_event(
        event_type=TaskEventType.CREATED.value,
        task_id=task_id,
        task_data=task_data,
        user_id=user_id
    )


async def publish_task_updated(
    task_id: int,
    task_data: Dict[str, Any],
    changes: Optional[Dict[str, Any]] = None,
    user_id: str = "anonymous"
) -> bool:
    """Publish task updated event.

    Args:
        task_id: The updated task ID
        task_data: The new task data
        changes: Dictionary of changed fields
        user_id: The user who updated the task

    Returns:
        True if published successfully
    """
    client = get_dapr_client()
    event_data = {**task_data}
    if changes:
        event_data["_changes"] = changes

    return await client.publish_task_event(
        event_type=TaskEventType.UPDATED.value,
        task_id=task_id,
        task_data=event_data,
        user_id=user_id
    )


async def publish_task_deleted(
    task_id: int,
    task_data: Dict[str, Any],
    user_id: str = "anonymous"
) -> bool:
    """Publish task deleted event.

    Args:
        task_id: The deleted task ID
        task_data: The deleted task data (for audit)
        user_id: The user who deleted the task

    Returns:
        True if published successfully
    """
    client = get_dapr_client()
    return await client.publish_task_event(
        event_type=TaskEventType.DELETED.value,
        task_id=task_id,
        task_data=task_data,
        user_id=user_id
    )


async def publish_task_completed(
    task_id: int,
    task_data: Dict[str, Any],
    user_id: str = "anonymous"
) -> bool:
    """Publish task completed event.

    Args:
        task_id: The completed task ID
        task_data: The task data
        user_id: The user who completed the task

    Returns:
        True if published successfully
    """
    client = get_dapr_client()
    return await client.publish_task_event(
        event_type=TaskEventType.COMPLETED.value,
        task_id=task_id,
        task_data=task_data,
        user_id=user_id
    )


async def publish_reminder_event(
    event_type: ReminderEventType,
    task_id: int,
    reminder_data: Dict[str, Any],
    user_id: str = "anonymous"
) -> bool:
    """Publish reminder event.

    Args:
        event_type: The reminder event type
        task_id: The associated task ID
        reminder_data: The reminder data
        user_id: The user associated with the reminder

    Returns:
        True if published successfully
    """
    client = get_dapr_client()
    event = {
        "type": event_type.value,
        "task_id": task_id,
        "data": reminder_data,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    return await client.publish_event(DaprTopic.REMINDERS.value, event)


async def publish_task_sync_event(
    event_type: str,
    task_data: Dict[str, Any],
    user_id: str = "anonymous"
) -> bool:
    """Publish task sync event for real-time updates.

    Args:
        event_type: The event type
        task_data: The task data
        user_id: The user who triggered the event

    Returns:
        True if published successfully
    """
    client = get_dapr_client()
    event = {
        "type": event_type,
        "data": task_data,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    return await client.publish_event(DaprTopic.TASK_UPDATES.value, event)


async def publish_audit_event(
    event_type: str,
    entity_id: int,
    entity_type: str,
    changes: Dict[str, Any],
    user_id: str = "anonymous"
) -> bool:
    """Publish audit event.

    Args:
        event_type: The audit event type
        entity_id: The entity ID
        entity_type: The entity type (e.g., "task")
        changes: The changes made
        user_id: The user who made the changes

    Returns:
        True if published successfully
    """
    client = get_dapr_client()
    event = {
        "type": event_type,
        "entity_id": entity_id,
        "entity_type": entity_type,
        "changes": changes,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    return await client.publish_event(DaprTopic.AUDIT_LOGS.value, event)
