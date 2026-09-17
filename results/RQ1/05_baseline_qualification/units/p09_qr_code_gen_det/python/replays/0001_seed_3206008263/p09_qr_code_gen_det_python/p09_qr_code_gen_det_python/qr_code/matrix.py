"""Matrix handling module for QR code implementation."""

from typing import List, Tuple

# Constants for QR code matrix
SIZE = 21
FINDER_SIZE = 5

def place_finder_patterns(matrix: List[List[int]]) -> None:
    """Place finder patterns at three fixed positions.
    
    Args:
        matrix: 2D list representing the QR code matrix
        
    Raises:
        ValueError: If matrix dimensions are incorrect
    """
    if len(matrix) != SIZE or any(len(row) != SIZE for row in matrix):
        raise ValueError(f"Matrix must be {SIZE}x{SIZE}")
    
    # Define the finder pattern (5x5)
    # Border: 1, Inner ring: 0, Center: 1
    finder_pattern = [
        [1, 1, 1, 1, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 1, 0, 1],
        [1, 0, 0, 0, 1],
        [1, 1, 1, 1, 1]
    ]
    
    # Positions for finder patterns: top-left, top-right, bottom-left
    positions = [(0, 0), (0, SIZE - FINDER_SIZE), (SIZE - FINDER_SIZE, 0)]
    
    for row_offset, col_offset in positions:
        for i in range(FINDER_SIZE):
            for j in range(FINDER_SIZE):
                matrix[row_offset + i][col_offset + j] = finder_pattern[i][j]


def data_positions() -> List[Tuple[int, int]]:
    """Return list of data position coordinates in row-major order.
    
    Returns:
        List of (row, column) tuples for data cells
    """
    positions = []
    
    # Generate all positions in the matrix
    for row in range(SIZE):
        for col in range(SIZE):
            # Skip finder pattern areas
            if _is_finder_position(row, col):
                continue
            positions.append((row, col))
    
    return positions


def _is_finder_position(row: int, col: int) -> bool:
    """Check if a position falls within any finder pattern.
    
    Args:
        row: Row index
        col: Column index
        
    Returns:
        True if position is part of a finder pattern
    """
    # Top-left finder pattern
    if 0 <= row < FINDER_SIZE and 0 <= col < FINDER_SIZE:
        return True
    
    # Top-right finder pattern
    if 0 <= row < FINDER_SIZE and SIZE - FINDER_SIZE <= col < SIZE:
        return True
    
    # Bottom-left finder pattern
    if SIZE - FINDER_SIZE <= row < SIZE and 0 <= col < FINDER_SIZE:
        return True
    
    return False


def build_matrix(bits: List[int]) -> List[List[int]]:
    """Build a QR code matrix from a list of bits.
    
    Args:
        bits: List of bits (0 or 1) to embed in the matrix
        
    Returns:
        21x21 matrix with finder patterns placed and data bits written
        
    Raises:
        ValueError: If bits exceed capacity or contain invalid values
    """
    # Validate input bits
    for bit in bits:
        if bit != 0 and bit != 1:
            raise ValueError("Bits must be 0 or 1")
    
    # Create empty matrix
    matrix = [[0 for _ in range(SIZE)] for _ in range(SIZE)]
    
    # Place finder patterns
    place_finder_patterns(matrix)
    
    # Get data positions
    positions = data_positions()
    
    # Check capacity
    if len(bits) > len(positions):
        raise ValueError("Too many bits for matrix capacity")
    
    # Fill data bits
    for i, (row, col) in enumerate(positions):
        if i < len(bits):
            matrix[row][col] = bits[i]
        else:
            # Padding bits should be 0 (but we're just not setting them)
            break
    
    return matrix


def validate_matrix(matrix: object) -> bool:
    """Validate that a matrix meets QR code specifications.
    
    Args:
        matrix: Object to validate as a QR code matrix
        
    Returns:
        True if matrix is valid, False otherwise
    """
    # Must be a list of lists
    if not isinstance(matrix, list):
        return False
    
    # Must have correct number of rows
    if len(matrix) != SIZE:
        return False
    
    # Each row must have correct number of columns and be a list
    for row in matrix:
        if not isinstance(row, list) or len(row) != SIZE:
            return False
        # Each element must be 0 or 1
        for cell in row:
            if cell != 0 and cell != 1:
                return False
    
    # Must have valid finder patterns at correct positions
    # Check top-left finder pattern
    if not _check_finder_pattern(matrix, 0, 0):
        return False
    
    # Check top-right finder pattern
    if not _check_finder_pattern(matrix, 0, SIZE - FINDER_SIZE):
        return False
    
    # Check bottom-left finder pattern
    if not _check_finder_pattern(matrix, SIZE - FINDER_SIZE, 0):
        return False
    
    return True


def _check_finder_pattern(matrix: List[List[int]], start_row: int, start_col: int) -> bool:
    """Check if a finder pattern at given position matches specification.
    
    Args:
        matrix: The QR code matrix
        start_row: Starting row index
        start_col: Starting column index
        
    Returns:
        True if finder pattern matches specification
    """
    # Finder pattern specification:
    # Border: 1, Inner ring: 0, Center: 1
    expected_pattern = [
        [1, 1, 1, 1, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 1, 0, 1],
        [1, 0, 0, 0, 1],
        [1, 1, 1, 1, 1]
    ]
    
    for i in range(FINDER_SIZE):
        for j in range(FINDER_SIZE):
            if matrix[start_row + i][start_col + j] != expected_pattern[i][j]:
                return False
    
    return True


def extract_bits(matrix: List[List[int]]) -> List[int]:
    """Extract data bits from a valid QR code matrix.
    
    Args:
        matrix: Valid QR code matrix
        
    Returns:
        List of bits (0 or 1) from data positions
        
    Raises:
        ValueError: If matrix is invalid or does not contain enough bits
    """
    if not validate_matrix(matrix):
        raise ValueError("Invalid matrix")
    
    # Get data positions
    positions = data_positions()
    
    # Extract bits from data positions
    bits = []
    for row, col in positions:
        bits.append(matrix[row][col])
    
    return bits