"""Runtime entry point for the press release system demonstration."""

from press_releases import (
    Contact,
    PressRelease,
    State,
    Template,
    validate_headline,
    validate_body,
    validate_contact,
    search_by_tag,
    search_text,
)
from press_releases.errors import DomainError
from press_releases.types import VersionEntry


def run_demo() -> dict[str, object]:
    """Run a demonstration of the press release lifecycle.

    This function creates a press release, validates it, submits it for review,
    publishes it, and performs searches. It returns a dictionary containing
    the final state and related information.

    Returns:
        A dictionary with keys 'release', 'state', 'versions', and 'rendered_text'
        representing the final state of the press release.
    """
    # Create a template
    template = Template("basic", "{{headline}}|{{body}}|{{contact_email}}")
    
    # Create a contact
    contact = Contact("Alice", "a@b.com")
    
    # Create a press release
    release = PressRelease(
        id="12345",
        headline="Hello",
        body="Body",
        contact=contact,
        template=template,
        custom_fields={"custom_field": "custom_value"}
    )
    
    # Validate the press release
    assert release.validate() is True
    
    # Add a tag
    release.add_tag("media")
    
    # Submit for review
    release.submit_for_review()
    
    # Publish the press release
    release.publish()
    
    # Get the version history
    versions = release.version_history()
    
    # Render the plain text
    rendered_text = release.render_plain_text()
    
    # Return the results
    return {
        "release": release,
        "state": release.state,
        "versions": versions,
        "rendered_text": rendered_text
    }


if __name__ == "__main__":
    # Run the demo
    result = run_demo()
    
    # Print the final state
    print(f"Final state: {result['state'].value}")