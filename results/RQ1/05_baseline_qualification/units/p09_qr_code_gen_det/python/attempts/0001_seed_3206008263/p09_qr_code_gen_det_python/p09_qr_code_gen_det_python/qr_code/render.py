"""Render module for QR code ASCII representation."""

from .matrix import validate_matrix


def render(matrix: list[list[int]], on: str = "##", off: str = "  ") -> str:
    """Render a QR code matrix as an ASCII string.
    
    Args:
        matrix: 21x21 QR code matrix to render
        on: String to use for dark cells (default: "##")
        off: String to use for light cells (default: "  ")
        
    Returns:
        ASCII representation of the QR code as a string with newlines
        
    Raises:
        ValueError: If matrix is invalid or marker strings are empty
    """
    # Validate matrix
    if not validate_matrix(matrix):
        raise ValueError("Invalid matrix")
    
    # Validate marker strings
    if not on or not off:
        raise ValueError("Marker strings cannot be empty")
    
    # Render each row
    lines = []
    for row in matrix:
        line = ""
        for cell in row:
            line += on if cell else off
        lines.append(line)
    
    # Join lines with newlines
    return "\n".join(lines)