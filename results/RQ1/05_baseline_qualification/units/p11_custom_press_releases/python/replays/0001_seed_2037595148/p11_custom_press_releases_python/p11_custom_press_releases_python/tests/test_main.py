"""Tests for the press release system demonstrating core functionality."""

from Main import run_demo
from press_releases import (
    DomainError,
    InvalidTransitionError,
    State,
    Contact,
    VersionEntry,
    Template,
    validate_headline,
    validate_body,
    validate_contact,
    PressRelease,
    search_by_tag,
    search_text,
)
import pytest


def test_run_demo_returns_dict_and_reaches_published():
    """Test that run_demo returns a dict and reaches PUBLISHED state."""
    result = run_demo()
    
    # Verify result is a dict
    assert isinstance(result, dict)
    
    # Verify the release is in PUBLISHED state
    assert result["state"] == State.PUBLISHED
    
    # Verify other expected keys exist
    assert "release" in result
    assert "versions" in result
    assert "rendered_text" in result


def test_template_rendering_validation_lifecycle_versioning():
    """Test template rendering, validation, lifecycle, and versioning."""
    # Create template and contact as specified in requirements
    template = Template("basic", "{{headline}}|{{body}}|{{contact_email}}")
    contact = Contact("Alice", "a@b.com")
    
    # Create press release with the specified values
    release = PressRelease(
        id="12345",
        headline="Hello",
        body="Body",
        contact=contact,
        template=template,
        custom_fields={"custom_field": "custom_value"}
    )
    
    # Verify rendering matches expected output
    expected_rendered = "Hello|Body|a@b.com"
    assert release.render_plain_text() == expected_rendered
    
    # Verify validation passes
    assert release.validate() is True
    
    # Test state transitions: DRAFT -> REVIEW -> PUBLISHED
    release.add_tag("media")
    release.submit_for_review()
    assert release.state == State.REVIEW
    
    release.publish()
    assert release.state == State.PUBLISHED
    
    # Verify version history has exactly one entry with number 1
    versions = release.version_history()
    assert len(versions) == 1
    assert versions[0].number == 1
    assert versions[0].rendered_text == expected_rendered


def test_invalid_candidate_validate_false_submit_raises_domain_error():
    """Test invalid candidate validation and transition errors."""
    # Create an invalid candidate with blank headline and invalid contact
    invalid_contact = Contact("", "invalid")
    invalid_release = PressRelease(
        id="67890",
        headline="",  # Blank headline
        body="Some body content",
        contact=invalid_contact,
        template=Template("test", "test"),
        custom_fields={}
    )
    
    # Verify validation fails without raising exception
    assert invalid_release.validate() is False
    
    # Verify submit_for_review raises DomainError for invalid content
    with pytest.raises(DomainError):
        invalid_release.submit_for_review()
    
    # Create a valid release that remains in DRAFT state
    valid_draft = PressRelease(
        id="54321",
        headline="Hello",
        body="Body",
        contact=Contact("Bob", "bob@example.com"),
        template=Template("test", "test"),
        custom_fields={}
    )
    
    # Immediately verify publish raises InvalidTransitionError before submit_for_review
    with pytest.raises(InvalidTransitionError):
        valid_draft.publish()
    
    # Add tags and verify insertion order preservation
    valid_draft.add_tag("media")
    valid_draft.add_tag("news")
    
    # Verify tags are in insertion order
    tags = valid_draft.tags()
    assert tags == ["media", "news"]
    
    # Test search_by_tag functionality
    releases = [valid_draft]
    media_results = search_by_tag(releases, "media")
    assert len(media_results) == 1
    assert media_results[0] == valid_draft
    
    # Test search_text functionality
    hello_results = search_text(releases, "hello")
    assert len(hello_results) == 1
    assert hello_results[0] == valid_draft