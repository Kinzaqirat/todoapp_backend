"""Unit tests for the Task model."""

import pytest
from datetime import datetime
from models import Task


def test_task_creation_minimal():
    """Test creating a task with minimal required fields."""
    task = Task(id=1, title="Test Task")
    
    assert task.id == 1
    assert task.title == "Test Task"
    assert task.description == ""
    assert task.completed is False
    assert task.priority is None
    assert task.tags == []
    assert task.due_date is None
    assert task.recurrence is None
    assert isinstance(task.created_at, datetime)
    assert isinstance(task.updated_at, datetime)


def test_task_creation_full():
    """Test creating a task with all fields."""
    now = datetime.now()
    task = Task(
        id=1,
        title="Test Task",
        description="Test description",
        completed=True,
        priority="high",
        tags=["work", "urgent"],
        due_date=now,
        recurrence="weekly",
        created_at=now,
        updated_at=now
    )
    
    assert task.id == 1
    assert task.title == "Test Task"
    assert task.description == "Test description"
    assert task.completed is True
    assert task.priority == "high"
    assert task.tags == ["work", "urgent"]
    assert task.due_date == now
    assert task.recurrence == "weekly"


def test_task_serialization():
    """Test task serialization to dict."""
    task = Task(id=1, title="Test Task", description="Test")
    task_dict = task.model_dump()
    
    assert task_dict["id"] == 1
    assert task_dict["title"] == "Test Task"
    assert task_dict["description"] == "Test"
    assert task_dict["completed"] is False
    assert "created_at" in task_dict
    assert "updated_at" in task_dict


def test_task_defaults():
    """Test that default values are set correctly."""
    task = Task(id=1, title="Test")
    
    assert task.description == ""
    assert task.completed is False
    assert task.tags == []
    assert task.priority is None
