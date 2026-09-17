"""Test suite for QR code implementation."""

import pytest
from Main import run_demo
from qr_code import (
    generate,
    decode,
    detect,
    render,
    validate_matrix,
    extract_bits,
    unpack_payload,
)


def test_run_demo_contract():
    """Test that run_demo returns the exact expected values."""
    result = run_demo()
    
    assert result["text"] == "CodeWM"
    assert result["decoded"] == "CodeWM"
    assert result["detected"] is True
    assert result["size"] == 21
    assert result["rendered_lines"] == 21


def test_unicode_roundtrip():
    """Test Unicode roundtrip with strict zero padding validation."""
    text = "hello-世界"
    matrix = generate(text)
    
    # Validate matrix and detection
    assert validate_matrix(matrix) is True
    assert detect(matrix) is True
    
    # Decode should work
    decoded = decode(matrix)
    assert decoded == text
    
    # Direct bit extraction and unpacking should also work
    bits = extract_bits(matrix)
    unpacked = unpack_payload(bits)
    assert unpacked.decode("utf-8") == text
    
    # Render should produce exactly 21 lines
    rendered = render(matrix)
    assert len(rendered.split("\n")) == 21


def test_corruption_and_malformed_rejection():
    """Test that corrupted and malformed matrices are properly rejected."""
    # Generate a valid matrix
    original_matrix = generate("test")
    
    # Test corruption: flip a bit in the finder pattern
    corrupted = [row[:] for row in original_matrix]
    corrupted[0][0] = 1 - corrupted[0][0]  # Flip the bit
    
    # Corrupted matrix should fail validation and detection
    assert validate_matrix(corrupted) is False
    assert detect(corrupted) is False
    
    # Decoding corrupted matrix should raise ValueError
    with pytest.raises(ValueError):
        decode(corrupted)
    
    # Test malformed 2x2 matrix
    malformed = [[0, 1], [1, 0]]
    assert validate_matrix(malformed) is False
    assert detect(malformed) is False