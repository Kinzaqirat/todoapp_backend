"""Storage layer for persisting tasks to JSON file."""

import json
import os
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
import calendar
from .models import Task, TaskPriority as Priority


class TaskStorage:
    """Handles reading and writing tasks to a JSON file.
    
    Attributes:
        file_path: Path to the JSON file storing tasks
    """
    
    def __init__(self, file_path: str = None):
        """Initialize the storage with a file path.
        
        Args:
            file_path: Path to the JSON file (default: TASKS_FILE_PATH or tasks.json)
        """
        if file_path is None:
            file_path = os.getenv("TASKS_FILE_PATH", "tasks.json")
        self.file_path = Path(file_path)
        self._ensure_file_exists()
    
    def _ensure_file_exists(self) -> None:
        """Create the tasks file if it doesn't exist."""
        if not self.file_path.exists():
            self.file_path.write_text("[]")
    
    def load_tasks(self) -> list[Task]:
        """Load all tasks from the JSON file.

        Returns:
            List of Task objects

        Raises:
            ValueError: If the JSON file is corrupted
        """
        try:
            data = json.loads(self.file_path.read_text())
            tasks = []
            for task_dict in data:
                # Convert ISO format strings back to datetime
                if task_dict.get("created_at"):
                    task_dict["created_at"] = datetime.fromisoformat(task_dict["created_at"])
                if task_dict.get("updated_at"):
                    task_dict["updated_at"] = datetime.fromisoformat(task_dict["updated_at"])
                if task_dict.get("due_date"):
                    task_dict["due_date"] = datetime.fromisoformat(task_dict["due_date"])
                # Ensure tags is a JSON string
                if "tags" in task_dict and isinstance(task_dict["tags"], list):
                    task_dict["tags"] = json.dumps(task_dict["tags"])
                tasks.append(Task(**task_dict))
            return tasks
        except json.JSONDecodeError as e:
            raise ValueError(f"Corrupted tasks file: {e}")
    
    def save_tasks(self, tasks: list[Task]) -> None:
        """Save all tasks to the JSON file.
        
        Args:
            tasks: List of Task objects to save
        """
        data = [task.model_dump(mode='json') for task in tasks]
        self.file_path.write_text(json.dumps(data, indent=2, default=str))
    
    def get_next_id(self) -> int:
        """Generate the next available task ID.
        
        Returns:
            Next unique task ID
        """
        tasks = self.load_tasks()
        if not tasks:
            return 1
        return max(task.id for task in tasks) + 1
    
    def add_task(
        self,
        title: str,
        description: str = "",
        priority: Optional["Priority"] = None,
        tags: Optional[list[str]] = None,
        due_date: Optional[datetime] = None
    ) -> Task:
        """Add a new task.

        Args:
            title: Task title
            description: Optional task description
            priority: Optional priority level
            tags: Optional list of tags
            due_date: Optional due date

        Returns:
            The newly created Task object
        """
        tasks = self.load_tasks()
        task = Task(
            id=self.get_next_id(),
            title=title,
            description=description,
            priority=priority,
            tags=json.dumps(tags or []),
            due_date=due_date
        )
        tasks.append(task)
        self.save_tasks(tasks)
        return task
    
    def get_all_tasks(self) -> list[Task]:
        """Get all tasks.
        
        Returns:
            List of Task objects.
        """
        return self.load_tasks()
    
    def get_task_by_id(self, task_id: int) -> Optional[Task]:
        """Get a specific task by ID.
        
        Args:
            task_id: The task ID to find
            
        Returns:
            Task object if found, None otherwise
        """
        tasks = self.load_tasks()
        for task in tasks:
            if task.id == task_id:
                return task
        return None
    
    def update_task(self, task_id: int, **updates) -> Optional[Task]:
        """Update a task's fields.
        
        Args:
            task_id: The task ID to update
            **updates: Field names and new values
            
        Returns:
            Updated Task object if found, None otherwise
        """
        all_tasks = self.load_tasks()
        for i, task in enumerate(all_tasks):
            if task.id == task_id:
                task_dict = task.model_dump()
                task_dict.update(updates)
                task_dict["updated_at"] = datetime.now()
                all_tasks[i] = Task(**task_dict)
                self.save_tasks(all_tasks)
                return all_tasks[i]
        return None
    
    def delete_task(self, task_id: int) -> bool:
        """Delete a task by ID.
        
        Args:
            task_id: The task ID to delete
            
        Returns:
            True if task was deleted, False if not found
        """
        all_tasks = self.load_tasks()
        initial_count = len(all_tasks)
        all_tasks = [task for task in all_tasks if task.id != task_id]
        if len(all_tasks) < initial_count:
            self.save_tasks(all_tasks)
            return True
        return False
    

    def complete_task(self, task_id: int) -> Optional[Task]:
        """Mark a task as completed.

        Args:
            task_id: The task ID to complete

        Returns:
            Updated Task object if found, None otherwise
        """
        all_tasks = self.load_tasks()
        for i, task in enumerate(all_tasks):
            if task.id == task_id:
                if task.completed:
                    return task  # Already completed

                task_dict = task.model_dump()
                task_dict["completed"] = True
                task_dict["completed_at"] = datetime.now()
                task_dict["updated_at"] = datetime.now()

                updated_task = Task(**task_dict)
                all_tasks[i] = updated_task

                self.save_tasks(all_tasks)
                return updated_task
        return None

    def toggle_complete(self, task_id: int) -> Optional[Task]:
        """Toggle a task's completion status.

        Args:
            task_id: The task ID to toggle

        Returns:
            Updated Task object if found, None otherwise
        """
        all_tasks = self.load_tasks()
        for i, task in enumerate(all_tasks):
            if task.id == task_id:
                task_dict = task.model_dump()
                is_completed = not task.completed

                task_dict["completed"] = is_completed
                task_dict["updated_at"] = datetime.now()
                if is_completed:
                    task_dict["completed_at"] = datetime.now()
                else:
                    task_dict["completed_at"] = None

                updated_task = Task(**task_dict)
                all_tasks[i] = updated_task

                self.save_tasks(all_tasks)
                return updated_task
        return None
    
    def search_tasks(self, keyword: str) -> list[Task]:
        """Search tasks by keyword in title or description.
        
        Args:
            keyword: Search keyword (case-insensitive)
            
        Returns:
            List of tasks matching the keyword
        """
        tasks = self.load_tasks()
        keyword_lower = keyword.lower()
        return [
            task for task in tasks
            if keyword_lower in task.title.lower() or keyword_lower in task.description.lower()
        ]
    
    def filter_tasks(
        self,
        tasks: list[Task], # Changed to take a list of tasks
        status: Optional[str] = None,
        priority: Optional[str] = None,
        tag: Optional[str] = None
    ) -> list[Task]:
        """Filter tasks by status, priority, or tag from a given list of tasks.
        
        Args:
            tasks: List of tasks to filter.
            status: Filter by status ('complete' or 'incomplete')
            priority: Filter by priority level ('high', 'medium', 'low')
            tag: Filter by tag (case-insensitive)
            
        Returns:
            List of filtered tasks
        """
        
        # Filter by status
        if status:
            if status == "complete":
                tasks = [task for task in tasks if task.completed]
            elif status == "incomplete":
                tasks = [task for task in tasks if not task.completed]
        
        # Filter by priority
        if priority:
            tasks = [task for task in tasks if task.priority and task.priority.value == priority]
        
        # Filter by tag
        if tag:
            tag_lower = tag.lower()
            filtered = []
            for task in tasks:
                task_tags = json.loads(task.tags) if isinstance(task.tags, str) else task.tags
                if tag_lower in [t.lower() for t in task_tags]:
                    filtered.append(task)
            tasks = filtered
        
        return tasks
    
    def sort_tasks(self, tasks: list[Task], sort_by: str) -> list[Task]:
        """Sort tasks by specified criteria from a given list of tasks.
        
        Args:
            tasks: List of tasks to sort
            sort_by: Sort criteria ('due-date', 'priority', 'title')
            
        Returns:
            Sorted list of tasks
        """
        if sort_by == "due-date":
            # Tasks with due dates first, sorted by date, then tasks without due dates
            with_due = [t for t in tasks if t.due_date]
            without_due = [t for t in tasks if not t.due_date]
            return sorted(with_due, key=lambda t: t.due_date) + without_due
        
        elif sort_by == "priority":
            # Define priority order
            priority_order = {"high": 0, "medium": 1, "low": 2, None: 3}
            return sorted(tasks, key=lambda t: priority_order.get(t.priority.value if t.priority else None, 3))
        
        elif sort_by == "title":
            return sorted(tasks, key=lambda t: t.title.lower())
        
        return tasks