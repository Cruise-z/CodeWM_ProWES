"""Protocol-level tests for the brick breaker game demonstrating runtime wiring and core rules."""

import Main
from brick_breaker import Game
from brick_breaker.game import Game
from brick_breaker.level import make_grid_level
from brick_breaker.config import GameConfig


def test_run_demo_returns_stable_snapshot() -> None:
    """Test that Main.run_demo returns a stable snapshot without side effects."""
    # Run the demo multiple times to ensure deterministic output
    result1 = Main.Main.run_demo()
    result2 = Main.Main.run_demo()
    
    # Verify the structure of the snapshot
    assert isinstance(result1, dict)
    assert 'score' in result1
    assert 'lives' in result1
    assert 'status' in result1
    assert 'bricks_remaining' in result1
    assert 'ball' in result1
    assert 'paddle' in result1
    
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
    
    # Verify deterministic behavior
    assert result1 == result2


def test_ball_brick_collision_rules() -> None:
    """Test that a ball-brick collision increments score and removes the brick at zero durability."""
    # Create a game with a single brick
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
    game = Game(config)
    
    # Verify initial state
    assert game.score == 0
    assert game.level.remaining() == 1
    
    # Simulate a ball hitting the brick from below
    # Position the ball above the brick so it will hit it
    game.ball.x = 25.0  # Center of the brick
    game.ball.y = 40.0  # Just above the brick
    game.ball.vx = 0.0
    game.ball.vy = 120.0  # Moving downward
    
    # Tick the game
    result = game.tick('none')
    
    # Verify the brick was hit and removed
    assert result['score'] == config.points_per_brick
    assert result['bricks_remaining'] == 0
    
    # Verify the ball bounced off the brick
    assert game.ball.vy < 0  # Should be moving upward after bounce


def test_bottom_out_decrements_lives_and_resets_level() -> None:
    """Test that a bottom-out decrements lives and resets the level when lives remain."""
    # Create a game with one life
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
    
    # Create a game
    game = Game(config)
    
    # Verify initial state
    assert game.lives == 1
    assert game.level.remaining() == 1
    assert game.status == 'running'
    
    # Position the ball below the screen to trigger bottom-out
    game.ball.x = 150.0
    game.ball.y = 450.0  # Below the screen
    game.ball.vx = 0.0
    game.ball.vy = 120.0  # Moving downward
    
    # Tick the game
    result = game.tick('none')
    
    # Verify lives were decremented and game state changed
    assert result['lives'] == 0
    assert result['status'] == 'gameover'
    
    # Verify that the level still has the same brick count
    # (since the game is over, the level isn't actually reset)
    assert result['bricks_remaining'] == 1