"""
Test suite for the brick breaker game protocol.

This file contains protocol-level tests that verify:
1. Runtime wiring via Main.run_demo returns a stable snapshot
2. Representative game rules work correctly:
   a) A ball-brick collision increments score and removes brick at zero durability
   b) A bottom-out decrements lives and resets level when lives remain
"""

import pytest
from Main import Main
from brick_breaker import Game, GameConfig
from brick_breaker.game import Game
from brick_breaker.level import make_grid_level
from brick_breaker.config import GameConfig


def test_run_demo_returns_stable_snapshot():
    """Test that Main.run_demo returns a consistent snapshot without side effects."""
    # Run the demo multiple times to ensure consistency
    result1 = Main.run_demo()
    result2 = Main.run_demo()
    
    # Verify identical results
    assert result1 == result2
    
    # Verify expected structure
    expected_keys = {"score", "lives", "status", "bricks_remaining", "ball", "paddle"}
    assert set(result1.keys()) == expected_keys
    
    # Verify nested structures
    assert set(result1["ball"].keys()) == {"x", "y", "vx", "vy"}
    assert set(result1["paddle"].keys()) == {"x", "y"}
    
    # Verify initial state values
    assert result1["score"] == 0
    assert result1["lives"] == 3
    assert result1["status"] == "running"
    assert result1["bricks_remaining"] == 15  # 3 rows * 5 cols


def test_ball_brick_collision_increments_score_and_removes_brick():
    """Test that a ball-brick collision increments score and removes brick at zero durability."""
    # Create a custom config for predictable testing
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
    
    # Create a game instance
    game = Game(config)
    
    # Manually position the ball to hit the brick directly
    # Place ball above the brick so it will hit it on next tick
    game.ball.x = 75.0  # Center of brick
    game.ball.y = 45.0  # Just above brick
    game.ball.vx = 0.0
    game.ball.vy = 120.0  # Moving downward
    
    # Store initial state
    initial_bricks_remaining = game.level.remaining()
    initial_score = game.score
    
    # Execute one tick (should hit the brick)
    result = game.tick("none")
    
    # Verify the brick was hit
    assert game.level.remaining() == initial_bricks_remaining - 1
    assert game.score == initial_score + config.points_per_brick
    
    # Verify the result includes updated state
    assert result["bricks_remaining"] == initial_bricks_remaining - 1
    assert result["score"] == initial_score + config.points_per_brick


def test_bottom_out_decrements_lives_and_resets_level():
    """Test that a bottom-out decrements lives and resets level when lives remain."""
    # Create a game with only one life for simplicity
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
        points_per_brick=100
    )
    
    # Create a game instance
    game = Game(config)
    
    # Position the ball so it goes below the screen
    game.ball.x = 150.0
    game.ball.y = 420.0  # Below the screen
    game.ball.vx = 0.0
    game.ball.vy = 120.0  # Moving downward
    
    # Store initial state
    initial_lives = game.lives
    
    # Execute one tick (should cause bottom-out)
    result = game.tick("none")
    
    # Verify lives were decremented
    assert game.lives == initial_lives - 1
    
    # Verify game status changed to gameover since lives reached 0
    assert game.status == "gameover"
    
    # Verify the result reflects the change
    assert result["lives"] == initial_lives - 1
    assert result["status"] == "gameover"
    
    # Verify ball and paddle were reset
    assert game.ball.x == 150.0  # Should be reset to original position
    assert game.ball.y == 360.0  # Should be reset above paddle
    assert game.ball.vx == 0.0   # Should have no horizontal velocity
    assert game.ball.vy == -120.0  # Should move upward again
    
    # Verify paddle was reset
    assert game.paddle.x == 150.0  # Should be centered
    assert game.paddle.y == 380.0  # Should be at bottom


def test_bottom_out_with_multiple_lives_resets_level():
    """Test that a bottom-out decrements lives and resets level when lives remain."""
    # Create a game with two lives
    config = GameConfig(
        width=300,
        height=400,
        lives=2,
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
    game = Game(config)
    
    # Position the ball so it goes below the screen
    game.ball.x = 150.0
    game.ball.y = 420.0  # Below the screen
    game.ball.vx = 0.0
    game.ball.vy = 120.0  # Moving downward
    
    # Store initial state
    initial_lives = game.lives
    initial_bricks_remaining = game.level.remaining()
    
    # Execute one tick (should cause bottom-out)
    result = game.tick("none")
    
    # Verify lives were decremented
    assert game.lives == initial_lives - 1
    
    # Verify game status is still running since lives remain
    assert game.status == "running"
    
    # Verify the result reflects the change
    assert result["lives"] == initial_lives - 1
    assert result["status"] == "running"
    
    # Verify all bricks are still present (level was reset)
    assert game.level.remaining() == initial_bricks_remaining
    
    # Verify ball and paddle were reset
    assert game.ball.x == 150.0  # Should be reset to original position
    assert game.ball.y == 360.0  # Should be reset above paddle
    assert game.ball.vx == 0.0   # Should have no horizontal velocity
    assert game.ball.vy == -120.0  # Should move upward again
    
    # Verify paddle was reset
    assert game.paddle.x == 150.0  # Should be centered
    assert game.paddle.y == 380.0  # Should be at bottom


def test_initial_game_state():
    """Test that the initial game state is correct."""
    config = GameConfig()
    game = Game(config)
    
    # Check initial configuration
    assert game.config == config
    assert game.score == 0
    assert game.lives == config.lives
    assert game.status == "running"
    
    # Check level creation
    assert game.level is not None
    assert game.level.remaining() == config.brick_rows * config.brick_cols
    
    # Check paddle position
    assert game.paddle.x == config.width / 2
    assert game.paddle.y == config.height - 20
    assert game.paddle.width == config.paddle_width
    assert game.paddle.speed == config.paddle_speed
    
    # Check ball position and velocity
    assert game.ball.x == config.width / 2
    assert game.ball.y == config.height - 40
    assert game.ball.vx == 0.0
    assert game.ball.vy == -config.ball_speed
    assert game.ball.radius == config.ball_radius