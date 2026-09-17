"""Filtering criteria and functions for tasks."""

from enum import Enum
from typing import List, Optional
from .entities import Task
from .priority import Priority


class TagMatchMode(Enum):
    """Mode for matching tags in filters."""

    ANY = "any"
    ALL = "all"


class FilterCriteria:
    """Criteria for filtering tasks."""

    def __init__(
        self,
        tags: Optional[List[str]] = None,
        tag_mode: TagMatchMode = TagMatchMode.ANY,
        include_completed: bool = False,
        priorities: Optional[List[Priority]] = None,
    ) -> None:
        """Initialize filter criteria.

        Args:
            tags: List of tags to match against.
            tag_mode: Whether to match any or all of the provided tags.
            include_completed: Whether to include completed tasks.
            priorities: List of priorities to filter by.
        """
        self.tags = tags or []
        self.tag_mode = tag_mode
        self.include_completed = include_completed
        self.priorities = priorities or []


def filter_tasks(tasks: List[Task], criteria: FilterCriteria) -> List[Task]:
    """Filter a list of tasks based on the given criteria.

    Args:
        tasks: List of tasks to filter.
        criteria: Filter criteria to apply.

    Returns:
        List of tasks that match the criteria.
    """
    result = tasks

    # Filter by priority
    if criteria.priorities:
        result = [task for task in result if task.priority in criteria.priorities]

    # Filter by tags
    if criteria.tags:
        if criteria.tag_mode == TagMatchMode.ANY:
            result = [
                task for task in result
                if any(tag in task.tags for tag in criteria.tags)
            ]
        elif criteria.tag_mode == TagMatchMode.ALL:
            result = [
                task for task in result
                if all(tag in task.tags for tag in criteria.tags)
            ]

    # Filter by completion status
    if not criteria.include_completed:
        result = [task for task in result if not task.completed]

    return result