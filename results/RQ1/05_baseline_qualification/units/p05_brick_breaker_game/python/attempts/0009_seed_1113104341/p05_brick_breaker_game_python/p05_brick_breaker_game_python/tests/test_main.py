"""Protocol-level tests for the brick breaker game."""

import pytest
from Main import Main
from brick_breaker import Game
from brick_breaker.game import Game as GameClass
from brick_breaker.level import make_grid_level
from brick_breaker.config import GameConfig


def test_run_demo_returns_stable_snapshot():
    """Test that Main.run_demo returns a stable snapshot without side effects."""
    # Run the demo multiple times to ensure consistency
    result1 = Main.run_demo()
    result2 = Main.run_demo()
    
    # Verify results are identical
    assert result1 == result2
    
    # Verify expected keys are present
    expected_keys = {
        "score", "lives", "status", "bricks_remaining",
        "ball", "paddle"
    }
    assert set(result1.keys()) == expected_keys
    
    # Verify nested structure
    assert "ball" in result1
    assert "paddle" in result1
    assert set(result1["ball"].keys()) == {"x", "y", "vx", "vy"}
    assert set(result1["paddle"].keys()) == {"x", "y"}
    
    # Verify initial state values
    assert result1["score"] == 0
    assert result1["lives"] == 3
    assert result1["status"] == "running"
    assert result1["bricks_remaining"] == 15  # 3 rows * 5 cols


def test_brick_hit_increments_score_and_removes_brick():
    """Test that a ball-brick collision increments score and removes the brick at zero durability."""
    # Create a game with a custom config for predictable testing
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
        points_per_brick=100,
    )
    
    # Create a game instance
    game = GameClass(config)
    
    # Manually position ball to hit the brick directly
    # Place ball above the brick and moving downward
    game.ball.x = 25.0  # Center of brick
    game.ball.y = 30.0  # Above brick
    game.ball.vx = 0.0
    game.ball.vy = 120.0  # Moving down
    
    # Ensure brick is alive
    assert game.level.bricks[0].alive()
    
    # Tick once to trigger collision
    result = game.tick("none")
    
    # Verify brick was hit and removed
    assert not game.level.bricks[0].alive()
    assert result["bricks_remaining"] == 0
    
    # Verify score was incremented
    assert result["score"] == 100


def test_bottom_out_decrements_lives_and_resets_level():
    """Test that a bottom-out decrements lives and resets level when lives remain."""
    # Create a game with minimal bricks for faster testing
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
        points_per_brick=100,
    )
    
    # Create a game instance
    game = GameClass(config)
    
    # Position ball below the bottom of the screen
    game.ball.x = 150.0
    game.ball.y = 450.0  # Below the screen
    game.ball.vx = 0.0
    game.ball.vy = 120.0  # Moving downward
    
    # Verify initial state
    assert game.lives == 3
    assert game.status == "running"
    assert game.level.remaining() == 1
    
    # Tick to trigger bottom-out
    result = game.tick("none")
    
    # Verify lives were decremented
    assert game.lives == 2
    assert result["lives"] == 2
    
    # Verify level was reset (still has the same brick count)
    assert game.level.remaining() == 1
    assert result["bricks_remaining"] == 1
    
    # Verify status is still running (not game over)
    assert game.status == "running"
    assert result["status"] == "running"
    
    # Verify ball was reset
    assert game.ball.x == 150.0
    assert game.ball.y == 380.0  # Just above paddle
    assert game.ball.vx == 0.0
    assert game.ball.vy == -120.0  # Moving upward again


def test_game_over_when_no_lives_left():
    """Test that game ends when all lives are lost."""
    # Create a game with minimal lives for quick testing
    config = GameConfig(
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
        points_per_brick=100,
    )
    
    # Create a game instance
    game = GameClass(config)
    
    # Position ball below the bottom of the screen
    game.ball.x = 150.0
    game.ball.y = 450.0  # Below the screen
    game.ball.vx = 0.0
    game.ball.vy = 120.0  # Moving downward
    
    # Verify initial state
    assert game.lives == 1
    assert game.status == "running"
    
    # Tick to trigger bottom-out
    result = game.tick("none")
    
    # Verify game is over
    assert game.lives == 0
    assert result["lives"] == 0
    assert game.status == "gameover"
    assert result["status"] == "gameover"