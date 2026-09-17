"""Protocol-level tests for the brick breaker game.

This module tests the runtime wiring and core game rules through
deterministic demonstration steps.
"""

import pytest
from Main import Main
from brick_breaker import Game
from brick_breaker.game import Game
from brick_breaker.level import make_grid_level
from brick_breaker.config import GameConfig


def test_run_demo_returns_stable_snapshot():
    """Test that Main.run_demo returns a stable snapshot without side effects."""
    # Run the demo multiple times to ensure determinism
    snapshot1 = Main.run_demo()
    snapshot2 = Main.run_demo()
    
    # Verify the snapshot structure and values
    assert isinstance(snapshot1, dict)
    assert 'score' in snapshot1
    assert 'lives' in snapshot1
    assert 'status' in snapshot1
    assert 'bricks_remaining' in snapshot1
    assert 'ball' in snapshot1
    assert 'paddle' in snapshot1
    
    # Verify initial state
    assert snapshot1['score'] == 0
    assert snapshot1['lives'] == 3
    assert snapshot1['status'] == 'running'
    assert snapshot1['bricks_remaining'] == 15  # 3 rows * 5 cols
    
    # Verify ball properties
    assert 'x' in snapshot1['ball']
    assert 'y' in snapshot1['ball']
    assert 'vx' in snapshot1['ball']
    assert 'vy' in snapshot1['ball']
    
    # Verify paddle properties
    assert 'x' in snapshot1['paddle']
    assert 'y' in snapshot1['paddle']
    
    # Ensure snapshots are identical (deterministic)
    assert snapshot1 == snapshot2


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
    
    # Create a game instance
    game = Game(config)
    
    # Move the ball to hit the brick
    # Position ball directly above the brick to simulate a direct hit
    game.ball.x = 25  # Center of the brick
    game.ball.y = 45  # Just above the brick
    game.ball.vx = 0.0
    game.ball.vy = 120.0  # Moving downward
    
    # Perform one tick to trigger collision
    result = game.tick('none')
    
    # Verify score increased
    assert result['score'] == 100  # Points for breaking one brick
    
    # Verify brick was removed
    assert result['bricks_remaining'] == 0
    
    # Verify game is still running
    assert result['status'] == 'running'


def test_bottom_out_decrements_lives_and_resets_level():
    """Test that a bottom-out decrements lives and resets level when lives remain."""
    # Create a game instance
    game = Game()
    
    # Move the ball below the screen to trigger bottom-out
    game.ball.y = 450  # Beyond the bottom of the screen
    game.ball.vy = 120.0  # Moving downward
    
    # Perform one tick to trigger bottom-out
    result = game.tick('none')
    
    # Verify lives decreased
    assert result['lives'] == 2  # One life lost
    
    # Verify game is still running (since lives > 0)
    assert result['status'] == 'running'
    
    # Verify bricks are reset
    assert result['bricks_remaining'] == 15  # Should be reset to initial count
    
    # Verify ball is reset
    assert result['ball']['y'] == 360  # Just above paddle
    assert result['ball']['vy'] == -120.0  # Moving upward
    assert result['ball']['vx'] == 0.0  # No horizontal velocity
    
    # Verify paddle is centered
    assert result['paddle']['x'] == 150.0  # Center of screen


def test_game_initialization():
    """Test that the game initializes correctly with default settings."""
    game = Game()
    
    # Check initial configuration
    assert game.config.width == 300
    assert game.config.height == 400
    assert game.config.lives == 3
    assert game.config.ball_speed == 120.0
    assert game.config.ball_radius == 4.0
    assert game.config.paddle_width == 60.0
    assert game.config.paddle_speed == 180.0
    assert game.config.brick_rows == 3
    assert game.config.brick_cols == 5
    assert game.config.points_per_brick == 100
    
    # Check initial state
    assert game.score == 0
    assert game.lives == 3
    assert game.status == 'running'
    
    # Check level creation
    assert len(game.level.bricks) == 15  # 3 rows * 5 cols
    assert game.level.remaining() == 15
    
    # Check paddle position
    assert game.paddle.x == 150.0  # Center of screen
    assert game.paddle.y == 380  # Near bottom
    assert game.paddle.width == 60.0
    assert game.paddle.speed == 180.0
    
    # Check ball position
    assert game.ball.x == 150.0  # Center of screen
    assert game.ball.y == 370  # Slightly above paddle
    assert game.ball.vx == 0.0
    assert game.ball.vy == -120.0  # Moving upward


def test_invalid_input_action_raises_value_error():
    """Test that invalid input actions raise ValueError."""
    game = Game()
    
    with pytest.raises(ValueError, match="Invalid input_action: invalid"):
        game.tick('invalid')
    
    with pytest.raises(ValueError, match="Invalid input_action: left_right"):
        game.tick('left_right')
    
    # These should work fine
    try:
        game.tick('left')
        game.tick('right')
        game.tick('none')
    except ValueError:
        pytest.fail("Valid actions should not raise ValueError")


def test_paddle_movement():
    """Test that paddle moves correctly with different inputs."""
    game = Game()
    
    # Store initial position
    initial_x = game.paddle.x
    
    # Move left
    game.tick('left')
    assert game.paddle.x < initial_x
    
    # Reset and move right
    game.paddle.x = initial_x
    game.tick('right')
    assert game.paddle.x > initial_x
    
    # Reset and don't move
    game.paddle.x = initial_x
    game.tick('none')
    assert game.paddle.x == initial_x


def test_wall_collisions():
    """Test ball wall collisions."""
    game = Game()
    
    # Test left wall collision
    game.ball.x = 4  # Right at the edge
    game.ball.vx = -120.0  # Moving left
    game.ball.y = 200  # Middle of screen
    
    game.tick('none')
    assert game.ball.x == 4  # Clamped to edge
    assert game.ball.vx == 120.0  # Reversed direction
    
    # Test right wall collision
    game.ball.x = 296  # Left at the edge
    game.ball.vx = 120.0  # Moving right
    game.ball.y = 200  # Middle of screen
    
    game.tick('none')
    assert game.ball.x == 296  # Clamped to edge
    assert game.ball.vx == -120.0  # Reversed direction
    
    # Test top wall collision
    game.ball.x = 150  # Middle of screen
    game.ball.y = 4  # Bottom at the edge
    game.ball.vy = -120.0  # Moving up
    
    game.tick('none')
    assert game.ball.y == 4  # Clamped to edge
    assert game.ball.vy == 120.0  # Reversed direction


def test_brick_removal_after_multiple_hits():
    """Test that bricks are properly removed after multiple hits."""
    # Create a config with single-durability bricks
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
    
    # Make the brick have durability of 3
    game.level.bricks[0].durability = 3
    
    # First hit
    game.ball.x = 25
    game.ball.y = 45
    game.ball.vx = 0.0
    game.ball.vy = 120.0
    result1 = game.tick('none')
    assert result1['score'] == 0  # Not yet broken
    assert result1['bricks_remaining'] == 1  # Still there
    
    # Second hit
    game.ball.y = 45
    game.ball.vy = 120.0
    result2 = game.tick('none')
    assert result2['score'] == 0  # Not yet broken
    assert result2['bricks_remaining'] == 1  # Still there
    
    # Third hit (breaking it)
    game.ball.y = 45
    game.ball.vy = 120.0
    result3 = game.tick('none')
    assert result3['score'] == 100  # Now broken
    assert result3['bricks_remaining'] == 0  # Removed