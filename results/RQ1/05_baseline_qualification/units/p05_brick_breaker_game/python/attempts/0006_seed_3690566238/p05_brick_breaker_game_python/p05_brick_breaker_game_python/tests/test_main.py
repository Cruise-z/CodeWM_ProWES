"""Protocol-level tests for the Brick Breaker game.

These tests verify the runtime wiring and core game rules:
1. Main.run_demo returns a stable snapshot without side effects
2. A ball-brick collision increments score and removes the brick at zero durability
3. A bottom-out decrements lives and resets the level when lives remain
"""

import pytest
from Main import Main
from brick_breaker import Game, GameConfig
from brick_breaker.game import Game as GameClass
from brick_breaker.level import make_grid_level
from brick_breaker.config import GameConfig as GameConfigClass


def test_run_demo_returns_stable_snapshot():
    """Test that Main.run_demo returns a deterministic snapshot."""
    # Run the demo multiple times to ensure consistency
    result1 = Main.run_demo()
    result2 = Main.run_demo()
    
    # Verify the structure and types
    assert isinstance(result1, dict)
    assert "score" in result1
    assert "lives" in result1
    assert "status" in result1
    assert "bricks_remaining" in result1
    assert "ball" in result1
    assert "paddle" in result1
    
    # Verify the ball structure
    assert isinstance(result1["ball"], dict)
    assert "x" in result1["ball"]
    assert "y" in result1["ball"]
    assert "vx" in result1["ball"]
    assert "vy" in result1["ball"]
    
    # Verify the paddle structure
    assert isinstance(result1["paddle"], dict)
    assert "x" in result1["paddle"]
    assert "y" in result1["paddle"]
    
    # Verify consistency between runs
    assert result1 == result2


def test_ball_brick_collision_increments_score_and_removes_brick():
    """Test that a ball-brick collision increments score and removes the brick at zero durability."""
    # Create a custom config for predictable testing
    config = GameConfigClass(
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
    
    # Create a game instance
    game = GameClass(config)
    
    # Get initial state
    initial_state = game.tick("none")
    initial_score = initial_state["score"]
    initial_bricks_remaining = initial_state["bricks_remaining"]
    
    # Move ball to hit the brick directly
    # Position ball to hit the brick from below
    game.ball.x = 25.0  # Center of the brick
    game.ball.y = 45.0  # Just above the brick
    game.ball.vx = 0.0
    game.ball.vy = 120.0  # Moving downward
    
    # Tick to process collision
    result = game.tick("none")
    
    # Verify score increased
    assert result["score"] == initial_score + config.points_per_brick
    
    # Verify brick was removed
    assert result["bricks_remaining"] == initial_bricks_remaining - 1
    
    # Verify game is still running
    assert result["status"] == "running"


def test_bottom_out_decrements_lives_and_resets_level():
    """Test that a bottom-out decrements lives and resets the level when lives remain."""
    # Create a custom config for predictable testing
    config = GameConfigClass(
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
    
    # Create a game instance
    game = GameClass(config)
    
    # Get initial state
    initial_state = game.tick("none")
    initial_lives = initial_state["lives"]
    
    # Position ball below the bottom of the screen to cause bottom-out
    game.ball.y = config.height + 10.0  # Well below the bottom
    
    # Tick to process bottom-out
    result = game.tick("none")
    
    # Verify lives decreased
    assert result["lives"] == initial_lives - 1
    
    # Verify game is still running (since lives > 0)
    assert result["status"] == "running"
    
    # Verify bricks are restored
    assert result["bricks_remaining"] == config.brick_rows * config.brick_cols
    
    # Verify ball and paddle were reset
    assert result["ball"]["x"] == config.width / 2
    assert result["ball"]["y"] == config.height - 30  # Slightly above paddle
    assert result["paddle"]["x"] == config.width / 2
    assert result["paddle"]["y"] == config.height - 20


def test_bottom_out_ends_game_when_no_lives():
    """Test that a bottom-out ends the game when no lives remain."""
    # Create a custom config with only one life
    config = GameConfigClass(
        width=300,
        height=400,
        lives=1,
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
    
    # Create a game instance
    game = GameClass(config)
    
    # Position ball below the bottom of the screen to cause bottom-out
    game.ball.y = config.height + 10.0  # Well below the bottom
    
    # Tick to process bottom-out
    result = game.tick("none")
    
    # Verify lives decreased to 0
    assert result["lives"] == 0
    
    # Verify game is over
    assert result["status"] == "gameover"