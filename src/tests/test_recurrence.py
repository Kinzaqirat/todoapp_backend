"""Unit tests for recurrence calculation in CRUD operations."""

import pytest
from datetime import datetime, timedelta
from crud import TaskStorage
from models import Task


class TestRecurrenceCalculation:
    """Tests for _calculate_next_due_date method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.storage = TaskStorage()

    def test_daily_recurrence(self):
        """Test daily recurrence adds 1 day."""
        current_due = datetime(2025, 12, 29, 9, 0)
        next_due = self.storage._calculate_next_due_date(current_due, "daily")

        assert next_due is not None
        assert next_due == datetime(2025, 12, 30, 9, 0)

    def test_weekly_recurrence(self):
        """Test weekly recurrence adds 7 days."""
        current_due = datetime(2025, 12, 29, 9, 0)
        next_due = self.storage._calculate_next_due_date(current_due, "weekly")

        assert next_due is not None
        assert next_due == datetime(2026, 1, 5, 9, 0)

    def test_monthly_recurrence_same_day(self):
        """Test monthly recurrence on a normal day."""
        current_due = datetime(2025, 1, 15, 9, 0)
        next_due = self.storage._calculate_next_due_date(current_due, "monthly")

        assert next_due is not None
        assert next_due.year == 2025
        assert next_due.month == 2
        assert next_due.day == 15

    def test_monthly_recurrence_end_of_month(self):
        """Test monthly recurrence handles months with fewer days."""
        # January 31 -> February (28 or 29)
        current_due = datetime(2025, 1, 31, 9, 0)
        next_due = self.storage._calculate_next_due_date(current_due, "monthly")

        assert next_due is not None
        assert next_due.month == 2
        assert next_due.day == 28  # 2025 is not a leap year

    def test_monthly_recurrence_year_rollover(self):
        """Test monthly recurrence rolls over to next year."""
        current_due = datetime(2025, 12, 15, 9, 0)
        next_due = self.storage._calculate_next_due_date(current_due, "monthly")

        assert next_due is not None
        assert next_due.year == 2026
        assert next_due.month == 1
        assert next_due.day == 15

    def test_unknown_recurrence_returns_none(self):
        """Test unknown recurrence pattern returns None."""
        current_due = datetime(2025, 12, 29, 9, 0)
        next_due = self.storage._calculate_next_due_date(current_due, "biweekly")

        assert next_due is None

    def test_daily_preserves_time(self):
        """Test that daily recurrence preserves the time component."""
        current_due = datetime(2025, 12, 29, 14, 30, 45)
        next_due = self.storage._calculate_next_due_date(current_due, "daily")

        assert next_due.hour == 14
        assert next_due.minute == 30
        assert next_due.second == 45

    def test_weekly_preserves_time(self):
        """Test that weekly recurrence preserves the time component."""
        current_due = datetime(2025, 12, 29, 8, 15)
        next_due = self.storage._calculate_next_due_date(current_due, "weekly")

        assert next_due.hour == 8
        assert next_due.minute == 15


class TestCompleteTaskWithRecurrence:
    """Tests for complete_task method with recurring tasks."""

    def setup_method(self):
        """Set up test fixtures with a fresh storage."""
        self.storage = TaskStorage()
        # Clear any existing tasks
        self.storage.save_tasks([])

    def teardown_method(self):
        """Clean up after tests."""
        self.storage.save_tasks([])

    def test_complete_non_recurring_task(self):
        """Test completing a non-recurring task doesn't create new task."""
        task = self.storage.add_task(title="One-time task")
        initial_count = len(self.storage.get_all_tasks())

        completed = self.storage.complete_task(task.id)

        assert completed is not None
        assert completed.completed is True
        assert len(self.storage.get_all_tasks()) == initial_count

    def test_complete_recurring_task_creates_next_instance(self):
        """Test completing a recurring task creates the next instance."""
        due_date = datetime(2025, 12, 29, 9, 0)
        task = self.storage.add_task(
            title="Daily standup",
            due_date=due_date,
            recurrence="daily"
        )
        initial_count = len(self.storage.get_all_tasks())

        completed = self.storage.complete_task(task.id)

        assert completed is not None
        assert completed.completed is True

        all_tasks = self.storage.get_all_tasks()
        assert len(all_tasks) == initial_count + 1

        # Find the new task
        new_task = [t for t in all_tasks if t.id != task.id and t.title == "Daily standup"][0]
        assert new_task.completed is False
        assert new_task.recurrence == "daily"
        assert new_task.due_date == datetime(2025, 12, 30, 9, 0)

    def test_complete_recurring_task_without_due_date(self):
        """Test completing a recurring task without due_date doesn't create new task."""
        task = self.storage.add_task(
            title="Recurring without date",
            recurrence="weekly"
        )
        initial_count = len(self.storage.get_all_tasks())

        completed = self.storage.complete_task(task.id)

        assert completed is not None
        assert len(self.storage.get_all_tasks()) == initial_count

    def test_complete_already_completed_task(self):
        """Test completing an already completed task returns it unchanged."""
        task = self.storage.add_task(title="Already done")
        self.storage.complete_task(task.id)

        # Try to complete again
        result = self.storage.complete_task(task.id)

        assert result is not None
        assert result.completed is True

    def test_complete_nonexistent_task(self):
        """Test completing a nonexistent task returns None."""
        result = self.storage.complete_task(99999)
        assert result is None

    def test_new_recurring_instance_preserves_attributes(self):
        """Test that new recurring task instance preserves priority, tags, etc."""
        from models import Priority

        due_date = datetime(2025, 12, 29, 9, 0)
        task = self.storage.add_task(
            title="Weekly review",
            description="Review weekly goals",
            priority=Priority.HIGH,
            tags=["work", "planning"],
            due_date=due_date,
            recurrence="weekly"
        )

        self.storage.complete_task(task.id)

        all_tasks = self.storage.get_all_tasks()
        new_task = [t for t in all_tasks if t.id != task.id and t.title == "Weekly review"][0]

        assert new_task.description == "Review weekly goals"
        assert new_task.priority == Priority.HIGH
        assert new_task.tags == ["work", "planning"]
        assert new_task.recurrence == "weekly"
