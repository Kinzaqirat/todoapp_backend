"""Unit tests for the chatbot service features."""

import pytest
from services.chatbot import (
    infer_priority,
    infer_recurrence,
    extract_tags,
    check_duplicate_task,
    get_task_summary,
    generate_proactive_context,
)


class TestPriorityInference:
    """Tests for priority inference from text."""

    def test_high_priority_urgent(self):
        """Test that 'urgent' triggers high priority."""
        assert infer_priority("This is urgent") == "high"

    def test_high_priority_asap(self):
        """Test that 'asap' triggers high priority."""
        assert infer_priority("Need this asap") == "high"

    def test_high_priority_critical(self):
        """Test that 'critical' triggers high priority."""
        assert infer_priority("Critical bug fix") == "high"

    def test_high_priority_important(self):
        """Test that 'important' triggers high priority."""
        assert infer_priority("Very important task") == "high"

    def test_low_priority_whenever(self):
        """Test that 'whenever' triggers low priority."""
        assert infer_priority("Do this whenever you can") == "low"

    def test_low_priority_someday(self):
        """Test that 'someday' triggers low priority."""
        assert infer_priority("Someday I'll do this") == "low"

    def test_low_priority_no_rush(self):
        """Test that 'no rush' triggers low priority."""
        assert infer_priority("No rush on this one") == "low"

    def test_default_medium_priority(self):
        """Test that normal text defaults to medium priority."""
        assert infer_priority("Buy groceries") == "medium"

    def test_case_insensitive(self):
        """Test that priority inference is case insensitive."""
        assert infer_priority("URGENT task") == "high"
        assert infer_priority("WHENEVER possible") == "low"


class TestRecurrenceInference:
    """Tests for recurrence pattern inference."""

    def test_daily_every_day(self):
        """Test 'every day' triggers daily recurrence."""
        assert infer_recurrence("Do this every day") == "daily"

    def test_daily_daily(self):
        """Test 'daily' triggers daily recurrence."""
        assert infer_recurrence("Daily standup meeting") == "daily"

    def test_daily_every_morning(self):
        """Test 'every morning' triggers daily recurrence."""
        assert infer_recurrence("Take vitamins every morning") == "daily"

    def test_weekly_every_week(self):
        """Test 'every week' triggers weekly recurrence."""
        assert infer_recurrence("Review goals every week") == "weekly"

    def test_weekly_weekly(self):
        """Test 'weekly' triggers weekly recurrence."""
        assert infer_recurrence("Weekly team sync") == "weekly"

    def test_weekly_specific_day(self):
        """Test specific weekday triggers weekly recurrence."""
        assert infer_recurrence("Meeting every monday") == "weekly"
        assert infer_recurrence("Call mom every sunday") == "weekly"

    def test_monthly_every_month(self):
        """Test 'every month' triggers monthly recurrence."""
        assert infer_recurrence("Pay rent every month") == "monthly"

    def test_monthly_monthly(self):
        """Test 'monthly' triggers monthly recurrence."""
        assert infer_recurrence("Monthly budget review") == "monthly"

    def test_no_recurrence(self):
        """Test that normal text returns None."""
        assert infer_recurrence("Buy groceries tomorrow") is None

    def test_case_insensitive(self):
        """Test that recurrence inference is case insensitive."""
        assert infer_recurrence("EVERY DAY workout") == "daily"


class TestTagExtraction:
    """Tests for tag extraction from text."""

    def test_work_tag_from_work(self):
        """Test 'work' keyword extracts work tag."""
        tags = extract_tags("This is a work task")
        assert "work" in tags

    def test_work_tag_from_office(self):
        """Test 'office' keyword extracts work tag."""
        tags = extract_tags("Office meeting tomorrow")
        assert "work" in tags

    def test_personal_tag_from_home(self):
        """Test 'home' keyword extracts personal tag."""
        tags = extract_tags("Clean the home")
        assert "personal" in tags

    def test_personal_tag_from_family(self):
        """Test 'family' keyword extracts personal tag."""
        tags = extract_tags("Family dinner")
        assert "personal" in tags

    def test_shopping_tag_from_groceries(self):
        """Test 'groceries' keyword extracts shopping tag."""
        tags = extract_tags("Buy groceries")
        assert "shopping" in tags

    def test_shopping_tag_from_buy(self):
        """Test 'buy' keyword extracts shopping tag."""
        tags = extract_tags("Buy new shoes")
        assert "shopping" in tags

    def test_health_tag_from_doctor(self):
        """Test 'doctor' keyword extracts health tag."""
        tags = extract_tags("Doctor appointment")
        assert "health" in tags

    def test_health_tag_from_gym(self):
        """Test 'gym' keyword extracts health tag."""
        tags = extract_tags("Go to the gym")
        assert "health" in tags

    def test_explicit_hashtag(self):
        """Test explicit hashtags are preserved."""
        tags = extract_tags("Task #custom #project")
        assert "custom" in tags
        assert "project" in tags

    def test_multiple_tags(self):
        """Test multiple tags can be extracted."""
        tags = extract_tags("Buy medicine from the store")
        assert "shopping" in tags
        assert "health" in tags

    def test_no_tags(self):
        """Test that generic text returns empty list."""
        tags = extract_tags("Do something")
        assert tags == []


class TestDuplicateDetection:
    """Tests for duplicate task detection."""

    def test_exact_match(self):
        """Test exact title match detection."""
        class MockTask:
            def __init__(self, title):
                self.title = title

        existing = [MockTask("Buy groceries"), MockTask("Call mom")]
        result = check_duplicate_task("Buy groceries", existing)
        assert result == "Buy groceries"

    def test_case_insensitive_match(self):
        """Test case insensitive matching."""
        class MockTask:
            def __init__(self, title):
                self.title = title

        existing = [MockTask("Buy Groceries")]
        result = check_duplicate_task("buy groceries", existing)
        assert result == "Buy Groceries"

    def test_no_match(self):
        """Test no match returns None."""
        class MockTask:
            def __init__(self, title):
                self.title = title

        existing = [MockTask("Buy groceries")]
        result = check_duplicate_task("Call mom", existing)
        assert result is None

    def test_fuzzy_match(self):
        """Test fuzzy matching for similar titles."""
        class MockTask:
            def __init__(self, title):
                self.title = title

        existing = [MockTask("Buy groceries from store")]
        result = check_duplicate_task("Buy groceries", existing)
        # Should match due to word overlap
        assert result is not None


class TestProactiveContext:
    """Tests for proactive context generation."""

    def test_overdue_alert(self):
        """Test overdue tasks generate alert."""
        summary = {"overdue": 2, "due_today": 0, "high_priority": 0}
        context = generate_proactive_context(summary)
        assert "overdue" in context.lower()

    def test_due_today_alert(self):
        """Test tasks due today generate alert."""
        summary = {"overdue": 0, "due_today": 3, "high_priority": 0}
        context = generate_proactive_context(summary)
        assert "due today" in context.lower()

    def test_high_priority_alert(self):
        """Test high priority tasks generate alert."""
        summary = {"overdue": 0, "due_today": 0, "high_priority": 5}
        context = generate_proactive_context(summary)
        assert "high-priority" in context.lower()

    def test_no_alerts(self):
        """Test no alerts when nothing urgent."""
        summary = {"overdue": 0, "due_today": 0, "high_priority": 0}
        context = generate_proactive_context(summary)
        assert context == ""

    def test_multiple_alerts(self):
        """Test multiple alerts are combined."""
        summary = {"overdue": 1, "due_today": 2, "high_priority": 3}
        context = generate_proactive_context(summary)
        assert "overdue" in context.lower()
        assert "due today" in context.lower()
        assert "high-priority" in context.lower()
