"""Template rendering for press releases."""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class Template:
    """A press release template with content and rendering capabilities."""

    name: str
    content: str

    def render(self, fields: Optional[Dict[str, str]] = None) -> str:
        """Render the template with provided field values.

        Replaces placeholders in the template content with values from fields.
        Placeholders are in the form {{key}} and are replaced with the corresponding
        value from fields. If a field is not provided, the placeholder is left unchanged.
        Placeholders are replaced in sorted order of keys.

        Args:
            fields: Dictionary mapping placeholder keys to their replacement values.
                    If None, an empty dictionary is used.

        Returns:
            The rendered template string with placeholders replaced.
        """
        values = {} if fields is None else fields
        result = self.content
        for key in sorted(values):
            placeholder = "{{" + key + "}}"
            result = result.replace(placeholder, values[key])
        return result