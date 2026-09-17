"""Protocol-level tests for the brick breaker game.

This module tests the runtime wiring and core game rules through
deterministic ticks and abstracted input.
"""

import pytest
from Main import Main
from brick_breaker import Game
from brick_breaker.game import Game as GameClass
from brick_breaker.level import make_grid_level
from brick_breaker.config import GameConfig


def test_run_demo_returns_stable_snapshot():
    """Test that Main.run_demo returns a stable snapshot without side effects."""
    # Run the demo multiple times to ensure determinism
    result1 = Main.run_demo()
    result2 = Main.run_demo()
    
    # Verify the structure of the snapshot
    assert 'score' in result1
    assert 'lives' in result1
    assert 'status' in result1
    assert 'bricks_remaining' in result1
    assert 'ball' in result1
    assert 'paddle' in result1
    
    # Verify consistent values across runs
    assert result1['score'] == result2['score']
    assert result1['lives'] == result2['lives']
    assert result1['status'] == result2['status']
    assert result1['bricks_remaining'] == result2['bricks_remaining']
    
    # Verify ball structure
    assert 'x' in result1['ball']
    assert 'y' in result1['ball']
    assert 'vx' in result1['ball']
    assert 'vy' in result1['ball']
    
    # Verify paddle structure
    assert 'x' in result1['paddle']
    assert 'y' in result1['paddle']


def test_ball_brick_collision_increments_score_and_removes_brick():
    """Test that a ball-brick collision increments score and removes the brick at zero durability."""
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
    
    # Create a game with a single brick
    game = GameClass(config)
    
    # Verify initial state
    assert game.level.remaining() == 1
    assert game.score == 0
    
    # Move the ball to intersect with the brick
    # Position the ball so it hits the brick
    game.ball.x = 30.0  # Center of the brick
    game.ball.y = 50.0  # Center of the brick
    game.ball.vx = 0.0
    game.ball.vy = 120.0  # Moving downwards
    
    # Perform a tick to trigger collision
    result = game.tick('none')
    
    # Verify that the brick is removed and score is incremented
    assert result['bricks_remaining'] == 0
    assert result['score'] == config.points_per_brick


def test_bottom_out_decrements_lives_and_resets_level():
    """Test that a bottom-out decrements lives and resets the level when lives remain."""
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
    
    # Create a game
    game = GameClass(config)
    
    # Verify initial state
    assert game.lives == 3
    assert game.level.remaining() == 1
    
    # Move the ball below the screen to trigger bottom-out
    game.ball.y = config.height + 10.0  # Below the bottom of the screen
    game.ball.vx = 0.0
    game.ball.vy = 120.0  # Moving downwards
    
    # Perform a tick to trigger bottom-out
    result = game.tick('none')
    
    # Verify that lives are decremented and level is reset
    assert result['lives'] == 2
    assert result['status'] == 'running'
    assert result['bricks_remaining'] == 1  # Level should be reset with same bricks
    
    # Verify that the ball and paddle are reset
    assert game.ball.x == config.width / 2  # Should be centered
    assert game.ball.y == config.height - 30  # Should be above paddle
    assert game.paddle.x == config.width / 2  # Should be centered
    assert game.paddle.y == config.height - 20  # Should be at bottom


def test_game_initialization():
    """Test game initialization with default settings."""
    # Create a game with default config
    game = GameClass()
    
    # Verify initial game state
    assert game.score == 0
    assert game.lives == 3
    assert game.status == 'running'
    
    # Verify that a grid level was created
    assert game.level is not None
    assert len(game.level.bricks) > 0
    
    # Verify paddle position
    assert game.paddle.x == game.config.width / 2
    assert game.paddle.y == game.config.height - 20
    
    # Verify ball position and velocity
    assert game.ball.x == game.paddle.x
    assert game.ball.y == game.paddle.y - 10
    assert game.ball.vx == 0.0
    assert game.ball.vy == -game.config.ball_speed


def test_invalid_input_raises_value_error():
    """Test that invalid input actions raise ValueError."""
    game = GameClass()
    
    # Test with invalid input
    with pytest.raises(ValueError):
        game.tick('invalid_input')
    
    # Test with another invalid input
    with pytest.raises(ValueError):
        game.tick('up')
    
    # Test with yet another invalid input
    with pytest.raises(ValueError):
        game.tick('down')
    
    # Test that valid inputs work
    try:
        game.tick('left')
        game.tick('right')
        game.tick('none')
    except ValueError:
        pytest.fail("Valid input actions should not raise ValueError")


def test_multiple_bricks_collision():
    """Test collision with multiple bricks in the level."""
    # Create a config with multiple bricks
    config = GameConfig(
        width=300,
        height=400,
        lives=3,
        ball_speed=120.0,
        ball_radius=4.0,
        paddle_width=60.0,
        paddle_speed=180.0,
        brick_rows=2,
        brick_cols=3,
        brick_width=50.0,
        brick_height=14.0,
        brick_padding=2.0,
        top_margin=40.0,
        points_per_brick=100
    )
    
    # Create a game
    game = GameClass(config)
    
    # Verify initial state
    assert game.level.remaining() == 6  # 2 rows * 3 columns
    assert game.score == 0
    
    # Move the ball into the first brick at the top
    game.ball.x = 30.0  # Center of first brick
    game.ball.y = 50.0  # Center of first brick
    game.ball.vx = 0.0
    game.ball.vy = 120.0  # Moving downwards
    
    # Perform a tick to trigger collision
    result = game.tick('none')
    
    # Verify that one brick is removed and score is incremented
    assert result['bricks_remaining'] == 5
    assert result['score'] == config.points_per_brick