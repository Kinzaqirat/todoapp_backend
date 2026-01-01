import os
from fastapi import APIRouter, HTTPException, status, Query, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from src.models import TaskPriority as Priority
from src.crud import TaskStorage, Task
from src.api.websocket import notify_task_change
from src.services.audit import audit_service
from src.events import publishers
from src.services.kafka_producer import get_kafka_producer

router = APIRouter()
storage = TaskStorage(file_path=os.getenv("TASKS_FILE_PATH", "tasks.json"))


async def emit_task_event(event_type: str, task_data: dict):
    """Emit a task event via WebSocket and Kafka."""
    # WebSocket notification
    await notify_task_change(event_type, task_data)

    # Kafka event publishing (try Dapr first, fallback to direct Kafka)
    task_id = task_data.get("id", 0)
    kafka_published = False

    try:
        # Try Dapr pub/sub first
        if event_type == "task.created":
            kafka_published = await publishers.publish_task_created(task_id, task_data)
        elif event_type == "task.updated":
            kafka_published = await publishers.publish_task_updated(task_id, task_data)
        elif event_type == "task.deleted":
            kafka_published = await publishers.publish_task_deleted(task_id, task_data)
        elif event_type == "task.completed":
            kafka_published = await publishers.publish_task_completed(task_id, task_data)
    except Exception:
        pass  # Dapr failed, try direct Kafka

    # Fallback to direct Kafka if Dapr failed
    if not kafka_published:
        producer = get_kafka_producer()
        producer.publish_task_event(event_type, task_id, task_data)


def log_task_audit(event_type: str, task_id: int, task_data: dict = None, old_data: dict = None):
    """Log task operation to audit service."""
    if event_type == "task.created":
        audit_service.log_task_created(task_id, task_data or {})
    elif event_type == "task.updated":
        audit_service.log_task_updated(task_id, old_data or {}, task_data or {})
    elif event_type == "task.deleted":
        audit_service.log_task_deleted(task_id, task_data or {})
    elif event_type == "task.completed":
        audit_service.log_task_completed(task_id, task_data.get("title", "Unknown") if task_data else "Unknown")

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[str] = "pending"
    priority: Optional[Priority] = Priority.MEDIUM
    tags: Optional[List[str]] = []
    due_date: Optional[datetime] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[Priority] = None
    tags: Optional[List[str]] = None
    due_date: Optional[datetime] = None

@router.post("/", response_model=Task, status_code=status.HTTP_201_CREATED)
async def create_task(task: TaskCreate, background_tasks: BackgroundTasks):
    new_task = storage.add_task(
        title=task.title,
        description=task.description or "",
        priority=task.priority,
        tags=task.tags,
        due_date=task.due_date
    )
    task_data = new_task.model_dump(mode='json')
    # Emit WebSocket event
    background_tasks.add_task(emit_task_event, "task.created", task_data)
    # Log to audit
    log_task_audit("task.created", new_task.id, task_data)
    return new_task

@router.get("/", response_model=List[Task])
async def get_tasks(
    status: Optional[str] = Query(None, regex="^(complete|incomplete)$"),
    priority: Optional[str] = Query(None, regex="^(high|medium|low)$"),
    tag: Optional[str] = None,
    sort_by: Optional[str] = Query(None, regex="^(due-date|priority|title)$")
):
    tasks = storage.get_all_tasks()
    tasks = storage.filter_tasks(tasks, status=status, priority=priority, tag=tag)
    if sort_by:
        tasks = storage.sort_tasks(tasks, sort_by=sort_by)
    return tasks

@router.get("/{task_id}", response_model=Task)
async def get_task(task_id: int):
    task = storage.get_task_by_id(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return task

@router.put("/{task_id}", response_model=Task)
async def update_task(task_id: int, task_update: TaskUpdate, background_tasks: BackgroundTasks):
    # Get old data for audit
    old_task = storage.get_task_by_id(task_id)
    old_data = old_task.model_dump(mode='json') if old_task else {}

    updated_task = storage.update_task(
        task_id,
        **task_update.model_dump(exclude_unset=True)
    )
    if not updated_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    task_data = updated_task.model_dump(mode='json')
    # Emit WebSocket event
    background_tasks.add_task(emit_task_event, "task.updated", task_data)
    # Log to audit
    log_task_audit("task.updated", task_id, task_data, old_data)
    return updated_task

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, background_tasks: BackgroundTasks):
    # Get task before deletion for event and audit
    task = storage.get_task_by_id(task_id)
    task_data = task.model_dump(mode='json') if task else {}
    success = storage.delete_task(task_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    # Emit WebSocket event
    if task:
        background_tasks.add_task(emit_task_event, "task.deleted", {"id": task_id, "title": task.title})
        # Log to audit
        log_task_audit("task.deleted", task_id, task_data)

@router.patch("/{task_id}/toggle-complete", response_model=Task)
async def toggle_task_complete(task_id: int, background_tasks: BackgroundTasks):
    task = storage.toggle_complete(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    task_data = task.model_dump(mode='json')
    # Emit WebSocket event
    event_type = "task.completed" if task.completed else "task.updated"
    background_tasks.add_task(emit_task_event, event_type, task_data)
    # Log to audit
    log_task_audit(event_type, task_id, task_data)
    return task

@router.get("/search/", response_model=List[Task])
async def search_tasks(keyword: str):
    return storage.search_tasks(keyword)