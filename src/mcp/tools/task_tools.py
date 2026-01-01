"""MCP tools for task management.

These tools allow AI to perform task operations via function calling.
"""

from typing import Optional, List
from datetime import datetime
from sqlmodel import Session, select
from models.task import Task, TaskStatus, TaskPriority
from events.publishers import (
    publish_task_created,
    publish_task_updated,
    publish_task_completed,
    publish_task_deleted
)
from services.dapr_client import get_dapr_client
from services.audit import audit_service
import logging

logger = logging.getLogger(__name__)


async def create_task(
    title: str,
    user_id: str,
    description: Optional[str] = None,
    priority: str = "medium",
    tags: Optional[List[str]] = None,
    due_date: Optional[datetime] = None,
    db: Session = None
) -> Task:
    """Create a new task and publish event.

    [Task]: T033
    [Acceptance Criteria]: Creates task, publishes event, returns task object

    Args:
        title: Task title (required)
        user_id: User who owns the task
        description: Optional detailed description
        priority: Task priority (low, medium, high)
        tags: List of category labels
        due_date: Optional due date and time
        db: Database session

    Returns:
        Created Task object
    """
    # Validate priority
    if priority not in [p.value for p in TaskPriority]:
        priority = "medium"

    task = Task(
        user_id=user_id,
        title=title,
        description=description or "",
        status=TaskStatus.PENDING.value,
        priority=priority,
        tags=tags or [],
        due_date=due_date
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # Publish event via Dapr
    await publish_task_created(
        task_id=task.id,
        task_data={
            "id": task.id,
            "title": task.title,
            "status": task.status,
            "priority": task.priority,
            "tags": task.tags,
            "due_date": task.due_date.isoformat() if task.due_date else None
        },
        user_id=user_id
    )

    # Log to audit
    audit_service.log_task_created(task.id, {
        "title": task.title,
        "priority": task.priority,
        "tags": task.tags
    })

    logger.info(f"Created task {task.id} for user {user_id}")
    return task


async def complete_task(
    task_id: int,
    user_id: str,
    db: Session = None
) -> Task:
    """Mark a task as completed and publish event.

    [Task]: T034
    [Acceptance Criteria]: Updates status, publishes event, returns task

    Args:
        task_id: Task to complete
        user_id: User requesting completion
        db: Database session

    Returns:
        Updated Task object

    Raises:
        ValueError: If task not found
    """
    task = db.get(Task, task_id)
    if not task:
        raise ValueError(f"Task {task_id} not found")

    task.status = TaskStatus.COMPLETED.value
    task.completed_at = datetime.utcnow()
    db.add(task)
    db.commit()
    db.refresh(task)

    # Publish event via Dapr
    await publish_task_completed(
        task_id=task.id,
        task_data={
            "id": task.id,
            "title": task.title,
            "status": task.status,
            "completed_at": task.completed_at.isoformat()
        },
        user_id=user_id
    )

    # Log to audit
    audit_service.log_task_completed(task.id, task.title)

    logger.info(f"Completed task {task_id} for user {user_id}")
    return task


async def delete_task(
    task_id: int,
    user_id: str,
    db: Session = None
) -> Task:
    """Soft delete a task and publish event.

    [Task]: T035
    [Acceptance Criteria]: Sets status to deleted, publishes event

    Args:
        task_id: Task to delete
        user_id: User requesting deletion
        db: Database session

    Returns:
        Updated Task object

    Raises:
        ValueError: If task not found
    """
    task = db.get(Task, task_id)
    if not task:
        raise ValueError(f"Task {task_id} not found")

    task.status = TaskStatus.DELETED.value
    db.add(task)
    db.commit()
    db.refresh(task)

    # Publish event via Dapr
    await publish_task_deleted(
        task_id=task.id,
        task_data={
            "id": task.id,
            "title": task.title,
            "status": task.status
        },
        user_id=user_id
    )

    # Log to audit
    audit_service.log_task_deleted(task.id, {
        "title": task.title,
        "status": task.status
    })

    logger.info(f"Deleted task {task_id} for user {user_id}")
    return task


async def update_task(
    task_id: int,
    user_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    tags: Optional[List[str]] = None,
    due_date: Optional[datetime] = None,
    db: Session = None
) -> Task:
    """Update task fields and publish event.

    [Task]: T036
    [Acceptance Criteria]: Updates specified fields, publishes event

    Args:
        task_id: Task to update
        user_id: User requesting update
        title: New title
        description: New description
        status: New status
        priority: New priority
        tags: New tags
        due_date: New due date
        db: Database session

    Returns:
        Updated Task object

    Raises:
        ValueError: If task not found
    """
    task = db.get(Task, task_id)
    if not task:
        raise ValueError(f"Task {task_id} not found")

    # Track changes for audit
    changes = {}

    if title is not None:
        changes["title"] = {"from": task.title, "to": title}
        task.title = title
    if description is not None:
        changes["description"] = {"from": task.description, "to": description}
        task.description = description
    if status is not None and status in [s.value for s in TaskStatus]:
        changes["status"] = {"from": task.status, "to": status}
        task.status = status
    if priority is not None and priority in [p.value for p in TaskPriority]:
        changes["priority"] = {"from": task.priority, "to": priority}
        task.priority = priority
    if tags is not None:
        changes["tags"] = {"from": task.tags, "to": tags}
        task.tags = tags
    if due_date is not None:
        changes["due_date"] = {"from": task.due_date, "to": due_date}
        task.due_date = due_date

    task.updated_at = datetime.utcnow()
    db.add(task)
    db.commit()
    db.refresh(task)

    # Publish event via Dapr
    await publish_task_updated(
        task_id=task.id,
        task_data={
            "id": task.id,
            "title": task.title,
            "status": task.status,
            "priority": task.priority,
            "tags": task.tags,
            "due_date": task.due_date.isoformat() if task.due_date else None
        },
        user_id=user_id
    )

    # Log to audit
    audit_service.log_task_updated(task.id, changes)

    logger.info(f"Updated task {task_id} for user {user_id}")
    return task


async def list_tasks(
    user_id: str,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    tag: Optional[str] = None,
    sort_by: Optional[str] = None,
    db: Session = None
) -> List[Task]:
    """List tasks with filtering and sorting.

    [Task]: T037
    [Acceptance Criteria]: Returns filtered, sorted tasks

    Args:
        user_id: User who owns the tasks
        status: Filter by status (pending, in_progress, completed)
        priority: Filter by priority (low, medium, high)
        tag: Filter by tag
        sort_by: Sort by field (priority, due_date, created_at)
        db: Database session

    Returns:
        List of Task objects
    """
    query = select(Task).where(Task.user_id == user_id)

    # Exclude deleted tasks unless explicitly requested
    if status != TaskStatus.DELETED.value:
        query = query.where(Task.status != TaskStatus.DELETED.value)

    # Apply filters
    if status and status in [s.value for s in TaskStatus]:
        query = query.where(Task.status == status)
    if priority and priority in [p.value for p in TaskPriority]:
        query = query.where(Task.priority == priority)
    if tag:
        # PostgreSQL array contains operator
        query = query.where(Task.tags.contains([tag]))

    # Apply sorting
    results = db.exec(query).all()

    if sort_by:
        if sort_by == "priority":
            priority_order = {"high": 0, "medium": 1, "low": 2}
            results.sort(key=lambda t: priority_order.get(t.priority, 3))
        elif sort_by == "due_date":
            results.sort(key=lambda t: t.due_date or datetime.max)
        elif sort_by == "created_at":
            results.sort(key=lambda t: t.created_at)

    logger.info(f"Listed {len(results)} tasks for user {user_id} with filters: status={status}, priority={priority}, tag={tag}")
    return results


async def search_tasks(
    user_id: str,
    keyword: str,
    db: Session = None
) -> List[Task]:
    """Search tasks by keyword in title.

    [Task]: T038
    [Acceptance Criteria]: Returns tasks matching keyword

    Args:
        user_id: User who owns the tasks
        keyword: Search keyword (case-insensitive)
        db: Database session

    Returns:
        List of matching Task objects
    """
    query = select(Task).where(
        Task.user_id == user_id,
        Task.status != TaskStatus.DELETED.value,
        Task.title.icontains(keyword)
    )

    results = db.exec(query).all()
    logger.info(f"Found {len(results)} tasks for user {user_id} with keyword '{keyword}'")
    return results


# Export all tools as a dictionary for MCP registration
MCP_TASK_TOOLS = {
    "create_task": create_task,
    "complete_task": complete_task,
    "delete_task": delete_task,
    "update_task": update_task,
    "list_tasks": list_tasks,
    "search_tasks": search_tasks,
}
