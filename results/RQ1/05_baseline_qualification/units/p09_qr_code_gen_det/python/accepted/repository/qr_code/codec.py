"""Codec module for QR code generation and detection."""

from .payload import encode_text, pack_payload, unpack_payload
from .matrix import build_matrix, extract_bits, validate_matrix


def generate(text: str) -> list[list[int]]:
    """Generate a QR code matrix from text.
    
    Args:
        text: Input text to encode
        
    Returns:
        21x21 QR code matrix represented as list of lists of integers (0 or 1)
    """
    # Encode text to bytes
    data = encode_text(text)
    
    # Pack payload into bits
    bits = pack_payload(data)
    
    # Build matrix from bits
    matrix = build_matrix(bits)
    
    return matrix


def decode(matrix: list[list[int]]) -> str:
    """Decode text from a QR code matrix.
    
    Args:
        matrix: 21x21 QR code matrix
        
    Returns:
        Decoded UTF-8 text
        
    Raises:
        ValueError: If matrix is invalid or payload is corrupt
    """
    # Extract bits from matrix
    bits = extract_bits(matrix)
    
    # Unpack payload from bits
    data = unpack_payload(bits)
    
    # Decode to UTF-8 string
    return data.decode("utf-8", errors="strict")


def detect(matrix: object) -> bool:
    """Detect if a matrix is a valid QR code.
    
    Args:
        matrix: Object to check for QR code validity
        
    Returns:
        True if matrix is a valid QR code, False otherwise
    """
    try:
        # Validate matrix first
        if not validate_matrix(matrix):
            return False
        
        # Try to decode - if successful, it's a valid QR code
        decode(matrix)
        return True
    except (ValueError, TypeError):
        # Any error during validation or decoding means it's not a valid QR code
        return False