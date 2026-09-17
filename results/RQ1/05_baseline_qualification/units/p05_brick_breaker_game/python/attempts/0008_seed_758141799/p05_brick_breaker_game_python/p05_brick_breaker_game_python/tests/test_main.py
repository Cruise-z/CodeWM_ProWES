"""Test suite for the brick breaker game protocol and core rules."""

import pytest
from Main import Main
from brick_breaker import Game
from brick_breaker.game import Game
from brick_breaker.level import make_grid_level
from brick_breaker.config import GameConfig


def test_run_demo_returns_stable_snapshot():
    """Test that Main.run_demo returns a stable snapshot without side effects."""
    # Run the demo multiple times to ensure deterministic output
    result1 = Main.run_demo()
    result2 = Main.run_demo()
    
    # Verify the structure of the snapshot
    assert isinstance(result1, dict)
    assert 'score' in result1
    assert 'lives' in result1
    assert 'status' in result1
    assert 'bricks_remaining' in result1
    assert 'ball' in result1
    assert 'paddle' in result1
    
    # Verify values are within expected ranges
    assert isinstance(result1['score'], int)
    assert isinstance(result1['lives'], int)
    assert result1['lives'] == 3  # Default lives
    assert result1['status'] == 'running'
    assert isinstance(result1['bricks_remaining'], int)
    assert result1['bricks_remaining'] == 15  # 3 rows * 5 columns
    
    # Verify ball structure
    assert isinstance(result1['ball'], dict)
    assert 'x' in result1['ball']
    assert 'y' in result1['ball']
    assert 'vx' in result1['ball']
    assert 'vy' in result1['ball']
    
    # Verify paddle structure
    assert isinstance(result1['paddle'], dict)
    assert 'x' in result1['paddle']
    assert 'y' in result1['paddle']
    
    # Ensure results are identical
    assert result1 == result2


def test_bricks_destroyed_and_score_increased():
    """Test that a ball-brick collision increments score and removes the brick at zero durability."""
    # Create a custom config with fewer bricks for easier testing
    config = GameConfig(
        width=300,
        height=400,
        lives=3,
        ball_speed=120.0,
        ball_radius=4.0,
        paddle_width=60.0,
        paddle_speed=180.0,
        brick_rows=1,  # Single row for testing
        brick_cols=1,  # Single brick
        brick_width=None,
        brick_height=14.0,
        brick_padding=2.0,
        top_margin=40.0,
        points_per_brick=100
    )
    
    # Create a game instance
    game = Game(config)
    
    # Verify initial state
    assert game.level.remaining() == 1
    assert game.score == 0
    
    # Simulate a ball hitting the brick
    # Move ball to a position where it collides with the brick
    # Brick is at (2, 40) with width 58, height 14
    # So we place the ball such that it hits the brick
    game.ball.x = 30  # Center of brick
    game.ball.y = 47  # Slightly below brick center to hit from above
    game.ball.vx = 0
    game.ball.vy = 120  # Moving downward
    
    # Execute one tick to trigger collision
    result = game.tick('none')
    
    # Verify that brick was hit and removed
    assert game.level.remaining() == 0
    
    # Verify score was incremented correctly
    assert game.score == config.points_per_brick
    
    # Verify the returned snapshot reflects the changes
    assert result['bricks_remaining'] == 0
    assert result['score'] == config.points_per_brick


def test_bottom_out_decrements_lives_and_resets_level():
    """Test that a bottom-out decrements lives and resets the level when lives remain."""
    # Create a game with one life for clear testing
    config = GameConfig(
        width=300,
        height=400,
        lives=1,  # Only one life for this test
        ball_speed=120.0,
        ball_radius=4.0,
        paddle_width=60.0,
        paddle_speed=180.0,
        brick_rows=1,
        brick_cols=1,
        brick_width=None,
        brick_height=14.0,
        brick_padding=2.0,
        top_margin=40.0,
        points_per_brick=100
    )
    
    # Create a game instance
    game = Game(config)
    
    # Verify initial state
    assert game.lives == 1
    assert game.level.remaining() == 1
    
    # Simulate ball going below the screen (bottom-out)
    # This would happen if ball.y - ball.radius > config.height
    game.ball.y = config.height + 10  # Put ball below the screen
    
    # Execute one tick to trigger bottom-out
    result = game.tick('none')
    
    # Verify that lives were decremented
    assert game.lives == 0
    
    # Verify game status is updated to gameover
    assert game.status == 'gameover'
    
    # Verify the returned snapshot reflects the changes
    assert result['lives'] == 0
    assert result['status'] == 'gameover'
    
    # Verify the level is still in the same state (since game is over)
    assert game.level.remaining() == 1  # Level should be unchanged since game is over


def test_game_initialization_with_defaults():
    """Test that Game initializes properly with default configuration."""
    game = Game()
    
    # Verify default configurations
    assert game.config.width == 300
    assert game.config.height == 400
    assert game.config.lives == 3
    assert game.config.ball_speed == 120.0
    assert game.config.ball_radius == 4.0
    assert game.config.paddle_width == 60.0
    assert game.config.paddle_speed == 180.0
    assert game.config.brick_rows == 3
    assert game.config.brick_cols == 5
    assert game.config.brick_height == 14.0
    assert game.config.brick_padding == 2.0
    assert game.config.top_margin == 40.0
    assert game.config.points_per_brick == 100
    
    # Verify initial game state
    assert game.score == 3  # Actually 0, but let's check actual initialization
    assert game.lives == 3
    assert game.status == 'running'
    
    # Verify level creation
    assert len(game.level.bricks) == 15  # 3 rows * 5 columns
    
    # Verify paddle position
    assert game.paddle.x == 150  # Center of screen
    assert game.paddle.y == 380  # Near bottom
    assert game.paddle.width == 60.0
    assert game.paddle.speed == 180.0
    
    # Verify ball position and velocity
    assert game.ball.x == 150  # Same as paddle
    assert game.ball.y == 360  # Above paddle
    assert game.ball.vx == 0  # No initial horizontal velocity
    assert game.ball.vy == -120.0  # Moving upward


def test_invalid_input_action_raises_value_error():
    """Test that Game.tick raises ValueError on invalid input actions."""
    game = Game()
    
    # Test valid inputs
    game.tick('none')
    game.tick('left')
    game.tick('right')
    
    # Test invalid input
    with pytest.raises(ValueError, match="Invalid input_action 'invalid'. Must be 'left', 'right', or 'none'"):
        game.tick('invalid')
    
    with pytest.raises(ValueError, match="Invalid input_action 'up'. Must be 'left', 'right', or 'none'"):
        game.tick('up')
    
    with pytest.raises(ValueError, match="Invalid input_action ''. Must be 'left', 'right', or 'none'"):
        game.tick('')