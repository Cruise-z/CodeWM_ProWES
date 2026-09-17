"""Canonical public API for the press release system."""

from .errors import DomainError, InvalidTransitionError
from .types import State, Contact, VersionEntry
from .template import Template
from .validation import validate_headline, validate_body, validate_contact
from .press_release import PressRelease
from .search import search_by_tag, search_text

# Re-export all canonical symbols
__all__ = [
    "DomainError",
    "InvalidTransitionError",
    "State",
    "Contact",
    "VersionEntry",
    "Template",
    "validate_headline",
    "validate_body",
    "validate_contact",
    "PressRelease",
    "search_by_tag",
    "search_text",
]