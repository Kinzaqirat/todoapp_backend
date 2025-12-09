"""Unit tests for the TaskStorage class."""

import pytest
import json
from pathlib import Path
from datetime import datetime, timedelta
from storage import TaskStorage
from models import Task


@pytest.fixture
def temp_storage(tmp_path):
    """Create a temporary storage for testing."""
    test_file = tmp_path / "test_tasks.json"
    return TaskStorage(str(test_file))


def test_storage_initialization(temp_storage):
    """Test that storage initializes with empty tasks file."""
    assert temp_storage.file_path.exists()
    tasks = temp_storage.load_tasks()
    assert tasks == []


def test_add_task(temp_storage):
    """Test adding a task."""
    task = temp_storage.add_task("Test Task", "Test description")
    
    assert task.id == 1
    assert task.title == "Test Task"
    assert task.description == "Test description"
    assert task.completed is False
    
    # Verify it's saved
    tasks = temp_storage.load_tasks()
    assert len(tasks) == 1
    assert tasks[0].title == "Test Task"


def test_add_task_with_due_date_and_recurrence(temp_storage):
    """Test adding a task with due date and recurrence."""
    due = datetime.now()
    task = temp_storage.add_task(
        "Recurring Task", 
        due_date=due,
        recurrence="daily"
    )
    
    assert task.due_date == due
    assert task.recurrence == "daily"
    
    # Verify persistence
    tasks = temp_storage.load_tasks()
    assert tasks[0].due_date == due
    assert tasks[0].recurrence == "daily"


def test_get_next_id(temp_storage):
    """Test ID generation."""
    assert temp_storage.get_next_id() == 1
    
    temp_storage.add_task("Task 1")
    assert temp_storage.get_next_id() == 2
    
    temp_storage.add_task("Task 2")
    assert temp_storage.get_next_id() == 3


def test_get_all_tasks(temp_storage):
    """Test retrieving all tasks."""
    temp_storage.add_task("Task 1")
    temp_storage.add_task("Task 2")
    temp_storage.add_task("Task 3")
    
    tasks = temp_storage.get_all_tasks()
    assert len(tasks) == 3
    assert tasks[0].title == "Task 1"
    assert tasks[1].title == "Task 2"
    assert tasks[2].title == "Task 3"


def test_get_task_by_id(temp_storage):
    """Test retrieving a specific task by ID."""
    temp_storage.add_task("Task 1")
    temp_storage.add_task("Task 2")
    
    task = temp_storage.get_task_by_id(1)
    assert task is not None
    assert task.title == "Task 1"
    
    task = temp_storage.get_task_by_id(2)
    assert task is not None
    assert task.title == "Task 2"
    
    task = temp_storage.get_task_by_id(999)
    assert task is None


def test_update_task(temp_storage):
    """Test updating a task."""
    temp_storage.add_task("Original Title", "Original description")
    
    updated = temp_storage.update_task(1, title="Updated Title")
    assert updated is not None
    assert updated.title == "Updated Title"
    assert updated.description == "Original description"
    
    updated = temp_storage.update_task(1, description="Updated description")
    assert updated.description == "Updated description"
    
    # Test updating non-existent task
    result = temp_storage.update_task(999, title="Test")
    assert result is None


def test_delete_task(temp_storage):
    """Test deleting a task."""
    temp_storage.add_task("Task 1")
    temp_storage.add_task("Task 2")
    
    result = temp_storage.delete_task(1)
    assert result is True
    
    tasks = temp_storage.get_all_tasks()
    assert len(tasks) == 1
    assert tasks[0].title == "Task 2"
    
    # Test deleting non-existent task
    result = temp_storage.delete_task(999)
    assert result is False


def test_toggle_complete(temp_storage):
    """Test toggling task completion status."""
    temp_storage.add_task("Test Task")
    
    # Toggle to complete
    task = temp_storage.toggle_complete(1)
    assert task is not None
    assert task.completed is True
    
    # Toggle back to incomplete
    task = temp_storage.toggle_complete(1)
    assert task.completed is False
    
    # Test toggling non-existent task
    result = temp_storage.toggle_complete(999)
    assert result is None


def test_recurrence_logic(temp_storage):
    """Test that completing a recurring task creates a new one."""
    due = datetime.now()
    temp_storage.add_task(
        "Daily Task",
        due_date=due,
        recurrence="daily"
    )
    
    # Complete the task
    task = temp_storage.toggle_complete(1)
    assert task.completed is True
    
    # Check for new task
    tasks = temp_storage.get_all_tasks()
    assert len(tasks) == 2
    
    new_task = tasks[1]
    assert new_task.title == "Daily Task"
    assert new_task.recurrence == "daily"
    assert new_task.completed is False
    # Check due date is roughly next day (ignoring microseconds diff)
    expected_due = due + timedelta(days=1)
    assert abs((new_task.due_date - expected_due).total_seconds()) < 1


def test_persistence(temp_storage):
    """Test that tasks persist across storage instances."""
    temp_storage.add_task("Task 1")
    temp_storage.add_task("Task 2")
    
    # Create new storage instance with same file
    new_storage = TaskStorage(str(temp_storage.file_path))
    tasks = new_storage.get_all_tasks()
    
    assert len(tasks) == 2
    assert tasks[0].title == "Task 1"
    assert tasks[1].title == "Task 2"


def test_datetime_serialization(temp_storage):
    """Test that datetime fields are properly serialized and deserialized."""
    task = temp_storage.add_task("Test Task")
    
    # Reload from file
    tasks = temp_storage.load_tasks()
    loaded_task = tasks[0]
    
    assert isinstance(loaded_task.created_at, datetime)
    assert isinstance(loaded_task.updated_at, datetime)

