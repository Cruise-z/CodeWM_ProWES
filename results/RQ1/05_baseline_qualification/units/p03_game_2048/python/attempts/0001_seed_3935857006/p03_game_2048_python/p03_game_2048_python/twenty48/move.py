"""Canonical implementation of the 2048 line merging logic."""

from typing import List, Tuple


def move_line_left(line: List[int]) -> Tuple[List[int], int]:
    """
    Apply the canonical left-moving merge logic to a line of up to 4 integers.
    
    Args:
        line: A list of up to 4 integers representing a row/column in the 2048 grid.
              Zeros represent empty cells.
              
    Returns:
        A tuple of (new_line, merge_score) where:
        - new_line is a list of 4 integers representing the result after the move,
          with zeros padded on the right if necessary
        - merge_score is the sum of all merged tile values
        
    Algorithm:
        1. Filter out zeros to create a compacted list
        2. Merge adjacent equal elements from left to right, updating the score
        3. Pad the result to length 4 with trailing zeros
    """
    # Step 1: Compact the line by removing zeros
    compacted = [x for x in line if x != 0]
    
    # Step 2: Merge adjacent equal elements
    merge_score = 0
    i = 0
    while i < len(compacted) - 1:
        if compacted[i] == compacted[i + 1]:
            # Merge the tiles
            merged_value = compacted[i] * 2
            compacted[i] = merged_value
            compacted[i + 1] = 0
            merge_score += merged_value
            i += 2  # Skip the next element as it's been merged
        else:
            i += 1
    
    # Step 3: Remove zeros again and pad to length 4
    merged = [x for x in compacted if x != 0]
    
    # Pad with zeros to ensure length 4
    while len(merged) < 4:
        merged.append(0)
        
    return (merged, merge_score)