from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from ..models import Priority
from ..crud import TaskStorage, Task

router = APIRouter()
storage = TaskStorage()

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
async def create_task(task: TaskCreate):
    return storage.add_task(
        title=task.title,
        description=task.description or "",
        priority=task.priority,
        tags=task.tags,
        due_date=task.due_date
    )

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
async def update_task(task_id: int, task_update: TaskUpdate):
    updated_task = storage.update_task(
        task_id, 
        **task_update.model_dump(exclude_unset=True)
    )
    if not updated_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return updated_task

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int):
    success = storage.delete_task(task_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

@router.patch("/{task_id}/toggle-complete", response_model=Task)
async def toggle_task_complete(task_id: int):
    task = storage.toggle_complete(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return task

@router.get("/search/", response_model=List[Task])
async def search_tasks(keyword: str):
    return storage.search_tasks(keyword)

