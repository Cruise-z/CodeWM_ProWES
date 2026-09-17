"""Public API for QR code generation and detection."""

from .payload import encode_text, pack_payload, unpack_payload
from .matrix import (
    SIZE,
    FINDER_SIZE,
    place_finder_patterns,
    data_positions,
    build_matrix,
    validate_matrix,
    extract_bits,
)
from .codec import generate, decode, detect
from .render import render

# Explicitly export all canonical functions
__all__ = [
    "encode_text",
    "pack_payload",
    "unpack_payload",
    "SIZE",
    "FINDER_SIZE",
    "place_finder_patterns",
    "data_positions",
    "build_matrix",
    "validate_matrix",
    "extract_bits",
    "generate",
    "decode",
    "detect",
    "render",
]