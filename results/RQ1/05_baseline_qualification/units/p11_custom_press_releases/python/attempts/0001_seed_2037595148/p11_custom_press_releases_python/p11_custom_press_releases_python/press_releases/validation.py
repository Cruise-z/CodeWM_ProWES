"""Validation rules for press release components."""

from typing import Dict, Optional

from .errors import DomainError
from .types import Contact


def validate_headline(headline: str) -> bool:
    """Validate that a headline is non-empty.

    Args:
        headline: The headline string to validate.

    Returns:
        True if the headline is non-empty, False otherwise.
    """
    return isinstance(headline, str) and headline.strip() != ""


def validate_body(body: str) -> bool:
    """Validate that a body is non-empty.

    Args:
        body: The body string to validate.

    Returns:
        True if the body is non-empty, False otherwise.
    """
    return isinstance(body, str) and body.strip() != ""


def validate_contact(contact: Contact) -> bool:
    """Validate a contact's name and email.

    A contact is valid if:
    - The name is non-empty
    - The email contains exactly one '@' character
    - Both sides of the '@' are non-empty

    Args:
        contact: The contact to validate.

    Returns:
        True if the contact is valid, False otherwise.
    """
    if not isinstance(contact, Contact):
        return False

    # Validate name
    if not isinstance(contact.name, str) or contact.name.strip() == "":
        return False

    # Validate email
    if not isinstance(contact.email, str):
        return False

    email_parts = contact.email.split("@")
    if len(email_parts) != 2:
        return False

    local_part, domain_part = email_parts
    if not local_part or not domain_part:
        return False

    return True