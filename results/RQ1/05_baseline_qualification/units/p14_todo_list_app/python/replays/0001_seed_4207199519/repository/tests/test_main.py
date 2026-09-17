"""Tests for the main demo functionality."""

from datetime import date
from Main import run_demo
from todo_app import (
    ApplicationService,
    InMemoryTaskRepository,
    FixedClock,
    Priority,
    SortKey,
    SortDirection,
    FilterCriteria,
    TagMatchMode,
    ValidationError,
)


def test_run_demo_returns_dict_and_works_with_fixed_clock():
    """Test that run_demo returns a dict and basic operations work with FixedClock."""
    # Run the demo
    result = run_demo()
    
    # Verify it returns a dict
    assert isinstance(result, dict)
    
    # Verify it has expected keys
    assert "tasks" in result
    assert "summary" in result
    
    # Verify tasks list is a list
    assert isinstance(result["tasks"], list)
    
    # Verify summary is a dict
    assert isinstance(result["summary"], dict)
    
    # Verify we can create and complete a task manually with FixedClock
    clock = FixedClock(date(2023, 10, 15))
    repo = InMemoryTaskRepository()
    service = ApplicationService(repo, clock)
    
    # Create a task
    task = service.create_task(
        title="Test task",
        priority="high"
    )
    
    # Complete it
    completed_task = service.complete_task(task.id)
    
    # List tasks
    tasks = service.list_tasks()
    
    # Verify task was completed
    assert completed_task.completed is True
    assert completed_task.completed_at == date(2023, 10, 15)
    
    # Verify we have one task
    assert len(tasks) == 1
    assert tasks[0].id == 1


def test_create_task_with_invalid_priority_raises_validation_error():
    """Test that creating a task with invalid priority raises ValidationError."""
    clock = FixedClock(date(2023, 10, 15))
    repo = InMemoryTaskRepository()
    service = ApplicationService(repo, clock)
    
    # This should raise ValidationError, not ValueError or other exceptions
    try:
        service.create_task("Test", priority="invalid")
        assert False, "Expected ValidationError to be raised"
    except ValidationError:
        # This is expected
        pass
    except Exception as e:
        assert False, f"Expected ValidationError, got {type(e).__name__}: {e}"


def test_sorting_by_due_date_with_equal_dates_sorts_by_id():
    """Test that tasks with equal due dates are sorted by ID."""
    clock = FixedClock(date(2023, 10, 15))
    repo = InMemoryTaskRepository()
    service = ApplicationService(repo, clock)
    
    # Create two tasks with the same due date
    task1 = service.create_task(
        title="First task",
        priority="high",
        due_date=date(2023, 10, 16)
    )
    
    task2 = service.create_task(
        title="Second task",
        priority="medium",
        due_date=date(2023, 10, 16)
    )
    
    # List tasks sorted by due date
    criteria = FilterCriteria(include_completed=True)
    sorted_tasks = service.list_tasks(
        criteria=criteria,
        sort_keys=[SortKey.DUE_DATE],
        direction=SortDirection.ASC
    )
    
    # First task should be the one with lower ID
    assert len(sorted_tasks) == 2
    assert sorted_tasks[0].id == 1
    assert sorted_tasks[1].id == 2


def test_completion_idempotence_and_summary():
    """Test that completing a task twice preserves completed_at and summary is correct."""
    clock = FixedClock(date(2023, 10, 15))
    repo = InMemoryTaskRepository()
    service = ApplicationService(repo, clock)
    
    # Create a task
    task = service.create_task(
        title="Test task",
        priority="high"
    )
    
    # Complete it once
    service.complete_task(task.id)
    
    # Complete it again (should be idempotent)
    service.complete_task(task.id)
    
    # Get summary
    summary = service.summary()
    
    # Verify summary values
    assert summary["total"] == 1
    assert summary["completed"] == 1
    assert summary["pending"] == 0
    assert summary["completed_today"] == 1
    
    # Verify priority counts
    assert summary["by_priority"]["HIGH"] == 1
    assert summary["by_priority"]["MEDIUM"] == 0
    assert summary["by_priority"]["LOW"] == 0
    
    # Verify completed_at is preserved
    tasks = service.list_tasks()
    assert tasks[0].completed_at == date(2023, 10, 15)