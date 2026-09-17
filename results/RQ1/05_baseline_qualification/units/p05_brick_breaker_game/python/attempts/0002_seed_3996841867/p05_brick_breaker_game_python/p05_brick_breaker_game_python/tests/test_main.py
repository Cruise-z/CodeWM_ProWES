"""
Test suite for the brick breaker game protocol.

This module contains protocol-level tests that verify:
1. Runtime wiring via Main.run_demo returns a stable snapshot
2. Representative game rules work correctly:
   - Brick hit increments score and removes brick at zero durability
   - Bottom-out decrements lives and resets level when lives remain
"""

import pytest
from Main import Main
from brick_breaker import Game
from brick_breaker.game import Game
from brick_breaker.level import make_grid_level
from brick_breaker.config import GameConfig


def test_run_demo_returns_stable_snapshot():
    """Test that Main.run_demo returns a consistent snapshot without side effects."""
    # Run the demo multiple times to ensure deterministic behavior
    snapshot1 = Main.run_demo()
    snapshot2 = Main.run_demo()
    
    # Verify the snapshot structure
    assert isinstance(snapshot1, dict)
    assert "score" in snapshot1
    assert "lives" in snapshot1
    assert "status" in snapshot1
    assert "bricks_remaining" in snapshot1
    assert "ball" in snapshot1
    assert "paddle" in snapshot1
    
    # Verify consistent values between runs
    assert snapshot1["score"] == snapshot2["score"]
    assert snapshot1["lives"] == snapshot2["lives"]
    assert snapshot1["status"] == snapshot2["status"]
    assert snapshot1["bricks_remaining"] == snapshot2["bricks_remaining"]
    
    # Verify ball structure
    assert isinstance(snapshot1["ball"], dict)
    assert "x" in snapshot1["ball"]
    assert "y" in snapshot1["ball"]
    assert "vx" in snapshot1["ball"]
    assert "vy" in snapshot1["ball"]
    
    # Verify paddle structure
    assert isinstance(snapshot1["paddle"], dict)
    assert "x" in snapshot1["paddle"]
    assert "y" in snapshot1["paddle"]


def test_brick_hit_increments_score_and_removes_brick():
    """Test that hitting a brick increments score and removes it when durability reaches zero."""
    # Create a custom config with fewer bricks for easier testing
    config = GameConfig(
        width=300,
        height=400,
        lives=3,
        ball_speed=120.0,
        ball_radius=4.0,
        paddle_width=60.0,
        paddle_speed=180.0,
        brick_rows=1,  # Single row for simplicity
        brick_cols=1,  # Single brick for simplicity
        brick_width=50.0,
        brick_height=14.0,
        brick_padding=2.0,
        top_margin=40.0,
        points_per_brick=100
    )
    
    # Create game with our config
    game = Game(config)
    
    # Verify initial state
    assert game.score == 0
    assert game.level.remaining() == 1  # One brick initially
    
    # Simulate a ball hit to the brick
    # First, we need to place the ball in a position where it will hit the brick
    # Put ball just above the brick
    game.ball.x = 25.0  # Center of the brick
    game.ball.y = 50.0  # Just above the brick
    game.ball.vx = 0.0
    game.ball.vy = 120.0  # Moving downward
    
    # Run one tick to trigger collision
    snapshot = game.tick("none")
    
    # Verify score was incremented
    assert game.score == config.points_per_brick
    
    # Verify brick was removed
    assert game.level.remaining() == 0
    
    # Verify snapshot reflects the changes
    assert snapshot["score"] == config.points_per_brick
    assert snapshot["bricks_remaining"] == 0


def test_bottom_out_decrements_lives_and_resets_level():
    """Test that a bottom-out event decrements lives and resets the level when lives remain."""
    # Create a custom config with known values
    config = GameConfig(
        width=300,
        height=400,
        lives=3,
        ball_speed=120.0,
        ball_radius=4.0,
        paddle_width=60.0,
        paddle_speed=180.0,
        brick_rows=1,
        brick_cols=1,
        brick_width=50.0,
        brick_height=14.0,
        brick_padding=2.0,
        top_margin=40.0,
        points_per_brick=100
    )
    
    # Create game with our config
    game = Game(config)
    
    # Store initial state
    initial_lives = game.lives
    initial_bricks = game.level.remaining()
    
    # Move ball below the paddle to trigger bottom-out
    game.ball.y = config.height + 10.0  # Below the bottom of the screen
    
    # Run one tick to trigger bottom-out
    snapshot = game.tick("none")
    
    # Verify lives were decremented
    assert game.lives == initial_lives - 1
    
    # Verify level was reset (same number of bricks)
    assert game.level.remaining() == initial_bricks
    
    # Verify game is still running (since lives > 0)
    assert game.status == "running"
    
    # Verify snapshot reflects the changes
    assert snapshot["lives"] == initial_lives - 1
    assert snapshot["status"] == "running"
    assert snapshot["bricks_remaining"] == initial_bricks
    
    # Test game over condition
    # Set lives to 1 and trigger another bottom-out
    game.lives = 1
    game.ball.y = config.height + 10.0
    
    # Run one tick to trigger final bottom-out
    snapshot = game.tick("none")
    
    # Verify game is now over
    assert game.status == "gameover"
    
    # Verify snapshot reflects game over
    assert snapshot["status"] == "gameover"