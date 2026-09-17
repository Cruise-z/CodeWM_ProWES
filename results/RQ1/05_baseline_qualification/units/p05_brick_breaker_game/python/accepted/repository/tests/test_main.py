"""Protocol-level tests for the brick breaker game.

This module verifies the runtime wiring and core game rules through
deterministic testing of the Main.run_demo function and key game mechanics.
"""

from Main import Main
from brick_breaker import Game
from brick_breaker.game import Game
from brick_breaker.level import make_grid_level
from brick_breaker.config import GameConfig


def test_run_demo_returns_stable_snapshot():
    """Verify that Main.run_demo returns a stable snapshot without side effects."""
    # Act
    result = Main.run_demo()
    
    # Assert
    assert isinstance(result, dict)
    assert 'score' in result
    assert 'lives' in result
    assert 'status' in result
    assert 'bricks_remaining' in result
    assert 'ball' in result
    assert 'paddle' in result
    
    # Verify ball structure
    assert 'x' in result['ball']
    assert 'y' in result['ball']
    assert 'vx' in result['ball']
    assert 'vy' in result['ball']
    
    # Verify paddle structure
    assert 'x' in result['paddle']
    assert 'y' in result['paddle']
    
    # Verify expected initial values
    assert result['score'] == 0
    assert result['lives'] == 3
    assert result['status'] == 'running'
    assert isinstance(result['bricks_remaining'], int)
    assert result['bricks_remaining'] > 0


def test_ball_brick_collision_increments_score_and_removes_brick():
    """Test that a ball-brick collision increments score and removes the brick at zero durability."""
    # Arrange
    config = GameConfig()
    game = Game(config)
    
    # Get the first brick
    first_brick = game.level.bricks[0]
    
    # Manually set ball position to hit the first brick
    # Position the ball so it collides with the first brick
    game.ball.x = first_brick.x + first_brick.width / 2
    game.ball.y = first_brick.y + first_brick.height / 2
    game.ball.vx = 0.0
    game.ball.vy = 10.0  # Moving downward
    
    # Store initial state
    initial_bricks_remaining = game.level.remaining()
    initial_score = game.score
    
    # Act
    result = game.tick('none')
    
    # Assert
    # Score should have increased
    assert result['score'] == initial_score + config.points_per_brick
    
    # Brick should be removed (assuming default durability of 1)
    assert result['bricks_remaining'] == initial_bricks_remaining - 1
    
    # The brick should no longer be alive
    assert not first_brick.alive()


def test_bottom_out_decrements_lives_and_resets_level():
    """Test that a bottom-out decrements lives and resets the level when lives remain."""
    # Arrange
    config = GameConfig(lives=3)
    game = Game(config)
    
    # Set ball to fall below the paddle to trigger bottom-out
    game.ball.y = config.height + 100  # Far below the game area
    game.ball.vx = 0.0
    game.ball.vy = 10.0  # Moving downward
    
    # Store initial state
    initial_lives = game.lives
    initial_bricks_remaining = game.level.remaining()
    
    # Act
    result = game.tick('none')
    
    # Assert
    # Lives should be decremented
    assert result['lives'] == initial_lives - 1
    
    # Level should be reset (same number of bricks)
    assert result['bricks_remaining'] == initial_bricks_remaining
    
    # Status should still be running (not gameover)
    assert result['status'] == 'running'
    
    # Ball and paddle should be reset to their starting positions
    assert game.ball.x == config.width / 2
    assert game.ball.y == config.height - 20 - 10
    assert game.paddle.x == config.width / 2
    assert game.paddle.y == config.height - 20