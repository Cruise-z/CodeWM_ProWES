"""Public API exports for the todo application."""

# Error types
from .errors import ValidationError, NotFoundError

# Domain entities
from .priority import Priority
from .entities import Task

# Filtering and sorting
from .filtering import TagMatchMode, FilterCriteria, filter_tasks
from .sorting import SortKey, SortDirection, sort_tasks

# Repository interface and implementation
from .repository import TaskRepository, InMemoryTaskRepository

# Clock interface and implementations
from .clock import Clock, SystemClock, FixedClock

# Application service
from .service import ApplicationService

# Explicitly define what is exported
__all__ = [
    "ValidationError",
    "NotFoundError",
    "Priority",
    "Task",
    "TagMatchMode",
    "FilterCriteria",
    "filter_tasks",
    "SortKey",
    "SortDirection",
    "sort_tasks",
    "TaskRepository",
    "InMemoryTaskRepository",
    "Clock",
    "SystemClock",
    "FixedClock",
    "ApplicationService",
]