"""Sorting criteria and functions for tasks."""

from enum import Enum
from typing import List, Optional
from .entities import Task
from .priority import Priority


class SortKey(Enum):
    """Keys by which tasks can be sorted."""

    DUE_DATE = "due_date"
    PRIORITY = "priority"
    TITLE = "title"
    COMPLETED = "completed"


class SortDirection(Enum):
    """Direction of sorting."""

    ASC = "asc"
    DESC = "desc"


def sort_tasks(
    tasks: List[Task],
    sort_keys: Optional[List[SortKey]] = None,
    direction: SortDirection = SortDirection.ASC,
) -> List[Task]:
    """Sort a list of tasks based on the given criteria.

    The sorting is stable and uses the provided sort keys in order.
    A final tie-break is made by task ID in ascending order.

    Args:
        tasks: List of tasks to sort.
        sort_keys: List of sort keys to apply in order.
        direction: Direction of sorting (ASC or DESC).

    Returns:
        List of tasks sorted according to the criteria.
    """
    if sort_keys is None:
        sort_keys = []

    # Default to sorting by ID if no keys provided
    if not sort_keys:
        sort_keys = [SortKey.TITLE]

    # Create a copy to avoid mutating the input
    result = tasks[:]

    # Apply sorting in reverse order of sort_keys to maintain stability
    for key in reversed(sort_keys):
        if key == SortKey.DUE_DATE:
            # For DUE_DATE, real dates come before None in ascending order
            result.sort(
                key=lambda t: (
                    t.due_date is None,
                    t.due_date,
                ),
                reverse=(direction == SortDirection.DESC),
            )
        elif key == SortKey.PRIORITY:
            result.sort(
                key=lambda t: t.priority.order_value(),
                reverse=(direction == SortDirection.DESC),
            )
        elif key == SortKey.TITLE:
            result.sort(
                key=lambda t: t.title,
                reverse=(direction == SortDirection.DESC),
            )
        elif key == SortKey.COMPLETED:
            result.sort(
                key=lambda t: t.completed,
                reverse=(direction == SortDirection.DESC),
            )

    # Final stable sort by ID to ensure deterministic results
    result.sort(key=lambda t: t.id)

    return result