"""Fundamental types for the press release system."""

from dataclasses import dataclass
from enum import Enum
from typing import Final


class State(Enum):
    """Represents the state of a press release."""

    DRAFT: Final = "DRAFT"
    REVIEW: Final = "REVIEW"
    PUBLISHED: Final = "PUBLISHED"


@dataclass(frozen=True)
class Contact:
    """Represents a contact person for a press release."""

    name: str
    email: str


@dataclass(frozen=True)
class VersionEntry:
    """Represents a version entry in the press release version history."""

    number: int
    rendered_text: str