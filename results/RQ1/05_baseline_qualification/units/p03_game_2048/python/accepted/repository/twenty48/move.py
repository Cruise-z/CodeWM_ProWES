"""Canonical move implementation for the 2048 game."""

from typing import List, Tuple


def move_line_left(line: List[int]) -> Tuple[List[int], int]:
    """
    Apply the canonical left move to a single line of the 2048 board.

    Args:
        line: A list of integers representing a row/column of the board.
              Length should be <= 4; zeros represent empty cells.

    Returns:
        A tuple of (new_line, merge_score) where:
        - new_line: A list of length 4 with zeros padded on the right
        - merge_score: The sum of all merged tile values during this move
    """
    # Step 1: Filter out zeros to create a compacted list
    compacted = [x for x in line if x != 0]

    # Step 2: Initialize variables for merging
    merge_score = 0
    i = 0

    # Step 3: Merge adjacent equal values
    while i < len(compacted) - 1:
        if compacted[i] == compacted[i + 1]:
            # Merge the tiles
            compacted[i] *= 2
            merge_score += compacted[i]
            compacted[i + 1] = 0
            i += 2  # Skip the next element as it's been merged
        else:
            i += 1

    # Step 4: Create the merged list by filtering out zeros again
    merged = [x for x in compacted if x != 0]

    # Step 5: Pad with zeros to ensure length 4
    while len(merged) < 4:
        merged.append(0)

    # Ensure we only have 4 elements
    merged = merged[:4]

    return merged, merge_score