"""Application service for managing tasks."""

from typing import List, Optional
from datetime import date
from .entities import Task
from .repository import TaskRepository
from .clock import Clock
from .priority import Priority
from .errors import ValidationError
from .filtering import FilterCriteria
from .sorting import SortKey, SortDirection


class ApplicationService:
    """Orchestrates task operations using repository and clock."""

    def __init__(self, repo: TaskRepository, clock: Clock) -> None:
        """Initialize the application service with a repository and clock.

        Args:
            repo: The task repository to use.
            clock: The clock to use for date operations.
        """
        self._repo = repo
        self._clock = clock

    def create_task(
        self,
        title: str,
        priority: Priority,
        description: Optional[str] = None,
        due_date: Optional[date] = None,
        tags: Optional[List[str]] = None,
    ) -> Task:
        """Create a new task.

        Args:
            title: The task title.
            priority: The task priority.
            description: Optional task description.
            due_date: Optional due date for the task.
            tags: Optional list of tags for the task.

        Returns:
            Task: The created task with assigned ID.

        Raises:
            ValidationError: If priority is invalid or title is blank.
        """
        # Convert priority if needed
        if isinstance(priority, str):
            priority = Priority.from_value(priority)

        # Create task with generated ID
        task_id = self._repo.next_id()
        task = Task(
            id=task_id,
            title=title.strip(),
            description=description,
            priority=priority,
            due_date=due_date,
            tags=tags or [],
            completed=False,
            completed_at=None,
        )

        # Add task to repository
        self._repo.add(task)
        return task

    def edit_task(
        self,
        task_id: int,
        title: Optional[str] = None,
        priority: Optional[Priority] = None,
        description: Optional[str] = None,
        due_date: Optional[date] = None,
        tags: Optional[List[str]] = None,
    ) -> Task:
        """Edit an existing task.

        Args:
            task_id: The ID of the task to edit.
            title: Optional new title.
            priority: Optional new priority.
            description: Optional new description.
            due_date: Optional new due date.
            tags: Optional new tags.

        Returns:
            Task: The updated task.

        Raises:
            NotFoundError: If the task does not exist.
        """
        # Get existing task
        task = self._repo.get(task_id)

        # Update fields if provided
        if title is not None:
            task.title = title.strip()
        if priority is not None:
            if isinstance(priority, str):
                priority = Priority.from_value(priority)
            task.priority = priority
        if description is not None:
            task.description = description
        if due_date is not None:
            task.due_date = due_date
        if tags is not None:
            task.tags = tags

        # Save changes
        self._repo.edit(task)
        return task

    def complete_task(self, task_id: int) -> Task:
        """Mark a task as complete.

        Args:
            task_id: The ID of the task to complete.

        Returns:
            Task: The completed task.

        Raises:
            NotFoundError: If the task does not exist.
        """
        task = self._repo.get(task_id)
        task.mark_complete_on(self._clock.today())
        self._repo.edit(task)
        return task

    def uncomplete_task(self, task_id: int) -> Task:
        """Mark a task as incomplete.

        Args:
            task_id: The ID of the task to mark incomplete.

        Returns:
            Task: The incomplete task.

        Raises:
            NotFoundError: If the task does not exist.
        """
        task = self._repo.get(task_id)
        task.mark_incomplete()
        self._repo.edit(task)
        return task

    def delete_task(self, task_id: int) -> None:
        """Delete a task.

        Args:
            task_id: The ID of the task to delete.

        Raises:
            NotFoundError: If the task does not exist.
        """
        self._repo.delete(task_id)

    def list_tasks(
        self,
        criteria: Optional[FilterCriteria] = None,
        sort_keys: Optional[List[SortKey]] = None,
        direction: SortDirection = SortDirection.ASC,
    ) -> List[Task]:
        """List tasks with optional filtering and sorting.

        Args:
            criteria: Optional filter criteria.
            sort_keys: Optional list of sort keys.
            direction: Sorting direction.

        Returns:
            List[Task]: The filtered and sorted list of tasks.
        """
        # Get all tasks
        tasks = self._repo.list_all()

        # Apply filtering if criteria provided
        if criteria is not None:
            from .filtering import filter_tasks
            tasks = filter_tasks(tasks, criteria)

        # Apply sorting if keys provided
        if sort_keys is not None:
            from .sorting import sort_tasks
            tasks = sort_tasks(tasks, sort_keys, direction)

        return tasks

    def summary(self) -> dict:
        """Get a summary of task statistics.

        Returns:
            dict: Summary with total, completed, pending, by_priority,
                  and completed_today counts.
        """
        tasks = self._repo.list_all()
        today = self._clock.today()

        total = len(tasks)
        completed = sum(1 for task in tasks if task.completed)
        pending = total - completed

        # Count by priority
        priority_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
        for task in tasks:
            priority_counts[task.priority.name] += 1

        # Count completed today
        completed_today = sum(
            1 for task in tasks
            if task.completed and task.completed_at == today
        )

        return {
            "total": total,
            "completed": completed,
            "pending": pending,
            "by_priority": priority_counts,
            "completed_today": completed_today,
        }