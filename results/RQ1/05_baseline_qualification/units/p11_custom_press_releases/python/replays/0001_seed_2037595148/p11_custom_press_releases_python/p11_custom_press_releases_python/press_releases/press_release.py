"""Mutable press release aggregate with lifecycle management."""

from typing import Dict, List, Optional
from .errors import DomainError, InvalidTransitionError
from .types import State, Contact, VersionEntry
from .template import Template
from .validation import validate_headline, validate_body, validate_contact


class PressRelease:
    """A mutable press release with lifecycle management."""

    def __init__(
        self,
        id: str,
        headline: str,
        body: str,
        contact: Contact,
        template: Template,
        custom_fields: Optional[Dict[str, str]] = None,
    ):
        """Initialize a press release.

        Note: This constructor deliberately does not validate inputs. Invalid
        values are allowed to be stored so that validate() can properly
        determine validity.

        Args:
            id: Unique identifier for the press release.
            headline: The press release headline.
            body: The press release body text.
            contact: The contact person for the press release.
            template: The template to use for rendering.
            custom_fields: Optional custom fields to be used in rendering.
        """
        self._id = id
        self._headline = headline
        self._body = body
        self._contact = contact
        self._template = template
        self._custom_fields = custom_fields if custom_fields is not None else {}
        self._state = State.DRAFT
        self._tags_list: List[str] = []
        self._tags_set: set[str] = set()
        self._versions: List[VersionEntry] = []

    @property
    def id(self) -> str:
        """Get the press release ID."""
        return self._id

    @property
    def headline(self) -> str:
        """Get the press release headline."""
        return self._headline

    @property
    def body(self) -> str:
        """Get the press release body."""
        return self._body

    @property
    def contact(self) -> Contact:
        """Get the press release contact."""
        return self._contact

    @property
    def state(self) -> State:
        """Get the current state of the press release."""
        return self._state

    def validate(self) -> bool:
        """Validate the press release.

        Returns:
            True if all fields are valid, False otherwise.
        """
        return (
            validate_headline(self._headline)
            and validate_body(self._body)
            and validate_contact(self._contact)
        )

    def submit_for_review(self) -> None:
        """Submit the press release for review.

        Raises:
            DomainError: If the press release is invalid.
        """
        if not self.validate():
            raise DomainError("Cannot submit for review: invalid press release")

        if self._state != State.DRAFT:
            raise InvalidTransitionError(
                f"Cannot submit for review: expected DRAFT, got {self._state.value}"
            )

        self._state = State.REVIEW

    def publish(self) -> None:
        """Publish the press release.

        Raises:
            InvalidTransitionError: If the press release is not in REVIEW state.
        """
        if self._state != State.REVIEW:
            raise InvalidTransitionError(
                f"Cannot publish: expected REVIEW, got {self._state.value}"
            )

        self._state = State.PUBLISHED

        # Append version history on first publish
        rendered_text = self.render_plain_text()
        version_entry = VersionEntry(number=1, rendered_text=rendered_text)
        self._versions.append(version_entry)

    def add_tag(self, tag: str) -> None:
        """Add a tag to the press release.

        Args:
            tag: The tag to add.

        Raises:
            DomainError: If the tag is blank.
        """
        # Trim whitespace
        trimmed_tag = tag.strip()
        if not trimmed_tag:
            raise DomainError("Tag cannot be blank")

        # Add only if not already present
        if trimmed_tag not in self._tags_set:
            self._tags_list.append(trimmed_tag)
            self._tags_set.add(trimmed_tag)

    def tags(self) -> List[str]:
        """Get the list of tags.

        Returns:
            A defensive copy of the tags list.
        """
        return self._tags_list.copy()

    def render_plain_text(self) -> str:
        """Render the press release as plain text.

        Combines custom fields with headline, body, and contact information,
        then renders using the template.

        Returns:
            The rendered plain text.
        """
        # Prepare fields for rendering
        fields = self._custom_fields.copy()
        fields["headline"] = self._headline
        fields["body"] = self._body
        fields["contact_name"] = self._contact.name
        fields["contact_email"] = self._contact.email

        return self._template.render(fields)

    def version_history(self) -> List[VersionEntry]:
        """Get the version history.

        Returns:
            A defensive copy of the version history list.
        """
        return self._versions.copy()