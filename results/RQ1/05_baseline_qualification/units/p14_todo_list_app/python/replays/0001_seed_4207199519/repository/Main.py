"""Runtime entry point for the todo application demo."""

from datetime import date
from todo_app import (
    ApplicationService,
    InMemoryTaskRepository,
    FixedClock,
    Task,
    Priority,
    SortKey,
    SortDirection,
    FilterCriteria,
    TagMatchMode,
)
from todo_app.service import ApplicationService


def run_demo() -> dict:
    """Run a demonstration of the todo application functionality.

    Returns:
        dict: A dictionary containing the demo results including tasks and summary.
    """
    # Create a fixed clock for deterministic behavior
    clock = FixedClock(date(2023, 10, 15))
    
    # Create repository and service
    repo = InMemoryTaskRepository()
    service = ApplicationService(repo, clock)
    
    # Create tasks
    task1 = service.create_task(
        title="Buy milk",
        priority="high",
        due_date=date(2023, 10, 16),
        tags=["shopping", "groceries"]
    )
    
    task2 = service.create_task(
        title="Read",
        priority="med",
        due_date=date(2023, 10, 16),
        tags=["books", "learning"]
    )
    
    # Complete the first task
    service.complete_task(task1.id)
    
    # List tasks sorted by due date
    criteria = FilterCriteria(include_completed=True)
    sorted_tasks = service.list_tasks(
        criteria=criteria,
        sort_keys=[SortKey.DUE_DATE],
        direction=SortDirection.ASC
    )
    
    # Get summary
    summary = service.summary()
    
    # Return results
    return {
        "tasks": sorted_tasks,
        "summary": summary,
    }


if __name__ == "__main__":
    result = run_demo()
    print("Demo executed successfully")