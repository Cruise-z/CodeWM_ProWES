"""Repository interface and in-memory implementation for tasks."""

from abc import ABC, abstractmethod
from typing import List
from .entities import Task
from .errors import NotFoundError, ValidationError


class TaskRepository(ABC):
    """Abstract base class for task repositories."""

    @abstractmethod
    def next_id(self) -> int:
        """Get the next available task ID.

        Returns:
            int: The next task ID.
        """

    @abstractmethod
    def add(self, task: Task) -> None:
        """Add a task to the repository.

        Args:
            task: The task to add.

        Raises:
            ValidationError: If a task with the same ID already exists.
        """

    @abstractmethod
    def get(self, task_id: int) -> Task:
        """Get a task by its ID.

        Args:
            task_id: The ID of the task to retrieve.

        Returns:
            Task: The retrieved task.

        Raises:
            NotFoundError: If no task with the given ID exists.
        """

    @abstractmethod
    def edit(self, task: Task) -> None:
        """Update an existing task in the repository.

        Args:
            task: The task to update.

        Raises:
            NotFoundError: If no task with the given ID exists.
        """

    @abstractmethod
    def delete(self, task_id: int) -> None:
        """Delete a task by its ID.

        Args:
            task_id: The ID of the task to delete.

        Raises:
            NotFoundError: If no task with the given ID exists.
        """

    @abstractmethod
    def list_all(self) -> List[Task]:
        """List all tasks in the repository.

        Returns:
            List[Task]: A list of all tasks, sorted by ID.
        """


class InMemoryTaskRepository(TaskRepository):
    """In-memory implementation of TaskRepository."""

    def __init__(self) -> None:
        """Initialize the in-memory task repository."""
        self._tasks: dict[int, Task] = {}
        self._next_id = 1

    def next_id(self) -> int:
        """Get the next available task ID.

        Returns:
            int: The next task ID.
        """
        return self._next_id

    def add(self, task: Task) -> None:
        """Add a task to the repository.

        Args:
            task: The task to add.

        Raises:
            ValidationError: If a task with the same ID already exists.
        """
        if task.id in self._tasks:
            raise ValidationError(f"Task with ID {task.id} already exists.")
        self._tasks[task.id] = task
        # Update next_id if needed
        if task.id >= self._next_id:
            self._next_id = task.id + 1

    def get(self, task_id: int) -> Task:
        """Get a task by its ID.

        Args:
            task_id: The ID of the task to retrieve.

        Returns:
            Task: The retrieved task.

        Raises:
            NotFoundError: If no task with the given ID exists.
        """
        try:
            return self._tasks[task_id]
        except KeyError:
            raise NotFoundError(f"Task with ID {task_id} not found.")

    def edit(self, task: Task) -> None:
        """Update an existing task in the repository.

        Args:
            task: The task to update.

        Raises:
            NotFoundError: If no task with the given ID exists.
        """
        if task.id not in self._tasks:
            raise NotFoundError(f"Task with ID {task.id} not found.")
        self._tasks[task.id] = task

    def delete(self, task_id: int) -> None:
        """Delete a task by its ID.

        Args:
            task_id: The ID of the task to delete.

        Raises:
            NotFoundError: If no task with the given ID exists.
        """
        try:
            del self._tasks[task_id]
        except KeyError:
            raise NotFoundError(f"Task with ID {task_id} not found.")

    def list_all(self) -> List[Task]:
        """List all tasks in the repository.

        Returns:
            List[Task]: A list of all tasks, sorted by ID.
        """
        # Return tasks sorted by ID
        return [self._tasks[i] for i in sorted(self._tasks.keys())]