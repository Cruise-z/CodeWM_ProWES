"""Test cases for the 2048 game implementation."""

from typing import List, Tuple
from Main import run_demo
from twenty48.move import move_line_left
from twenty48.types import Direction, GameStatus


def test_move_line_left_fixtures() -> None:
    """Test the canonical move_line_left behavior with various inputs."""
    # Test case 1: No merge needed
    result, score = move_line_left([2, 4, 8, 16])
    assert result == [2, 4, 8, 16], f"Expected [2, 4, 8, 16], got {result}"
    assert score == 0, f"Expected score 0, got {score}"

    # Test case 2: Single merge
    result, score = move_line_left([2, 2, 4, 8])
    assert result == [4, 4, 8, 0], f"Expected [4, 4, 8, 0], got {result}"
    assert score == 4, f"Expected score 4, got {score}"

    # Test case 3: Multiple merges, skip after merge
    result, score = move_line_left([2, 2, 2, 2])
    assert result == [4, 4, 0, 0], f"Expected [4, 4, 0, 0], got {result}"
    assert score == 8, f"Expected score 8, got {score}"

    # Test case 4: Padding to length 4
    result, score = move_line_left([2, 2, 0, 0])
    assert result == [4, 0, 0, 0], f"Expected [4, 0, 0, 0], got {result}"
    assert score == 4, f"Expected score 4, got {score}"

    # Test case 5: Empty line
    result, score = move_line_left([0, 0, 0, 0])
    assert result == [0, 0, 0, 0], f"Expected [0, 0, 0, 0], got {result}"
    assert score == 0, f"Expected score 0, got {score}"

    # Test case 6: Non-padding case with zeros in middle
    result, score = move_line_left([4, 0, 4, 0])
    assert result == [8, 0, 0, 0], f"Expected [8, 0, 0, 0], got {result}"
    assert score == 8, f"Expected score 8, got {score}"


def test_run_demo_smoke() -> None:
    """Smoke test for run_demo with seed 0."""
    # Call run_demo with seed 0
    status, score, tiles_count = run_demo(0)
    
    # Verify return types
    assert isinstance(status, GameStatus), f"Expected GameStatus, got {type(status)}"
    assert isinstance(score, int), f"Expected int, got {type(score)}"
    assert isinstance(tiles_count, int), f"Expected int, got {type(tiles_count)}"
    
    # Verify deterministic behavior by running twice with same seed
    status2, score2, tiles_count2 = run_demo(0)
    assert status == status2, "Status should be deterministic"
    assert score == score2, "Score should be deterministic"
    assert tiles_count == tiles_count2, "Tiles count should be deterministic"
    
    # Verify reasonable values for status
    assert status in [GameStatus.RUNNING, GameStatus.WON, GameStatus.LOST], \
        f"Unexpected status: {status}"
        
    # Verify score is non-negative
    assert score >= 0, f"Score should be non-negative, got {score}"
    
    # Verify tiles count is between 0 and 16
    assert 0 <= tiles_count <= 16, f"Tiles count should be between 0 and 16, got {tiles_count}"