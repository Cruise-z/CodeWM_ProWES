"""Test suite for the brick breaker game protocol.

This module tests the runtime wiring and core game rules through
deterministic demonstrations and assertions.
"""

from Main import Main
from brick_breaker import Game
from brick_breaker.game import Game
from brick_breaker.level import make_grid_level
from brick_breaker.config import GameConfig


def test_run_demo_returns_stable_snapshot():
    """Test that Main.run_demo returns a stable snapshot without side effects."""
    # Run the demo once
    snapshot = Main.run_demo()
    
    # Verify the snapshot structure and content
    assert isinstance(snapshot, dict)
    assert 'score' in snapshot
    assert 'lives' in snapshot
    assert 'status' in snapshot
    assert 'bricks_remaining' in snapshot
    assert 'ball' in snapshot
    assert 'paddle' in snapshot
    
    # Verify basic types
    assert isinstance(snapshot['score'], int)
    assert isinstance(snapshot['lives'], int)
    assert isinstance(snapshot['status'], str)
    assert isinstance(snapshot['bricks_remaining'], int)
    assert isinstance(snapshot['ball'], dict)
    assert isinstance(snapshot['paddle'], dict)
    
    # Verify ball structure
    ball = snapshot['ball']
    assert 'x' in ball
    assert 'y' in ball
    assert 'vx' in ball
    assert 'vy' in ball
    assert isinstance(ball['x'], float)
    assert isinstance(ball['y'], float)
    assert isinstance(ball['vx'], float)
    assert isinstance(ball['vy'], float)
    
    # Verify paddle structure
    paddle = snapshot['paddle']
    assert 'x' in paddle
    assert 'y' in paddle
    assert isinstance(paddle['x'], float)
    assert isinstance(paddle['y'], float)
    
    # Verify initial game state
    assert snapshot['score'] == 0
    assert snapshot['lives'] == 3
    assert snapshot['status'] == 'running'
    assert snapshot['bricks_remaining'] == 15  # 3 rows * 5 cols


def test_ball_brick_collision_increments_score_and_removes_brick():
    """Test that a ball-brick collision increments score and removes the brick at zero durability."""
    # Create a game with a custom config for easier testing
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
    
    # Manually place ball above the brick to ensure collision
    # Position ball so it will hit the brick
    game.ball.x = 100
    game.ball.y = 50
    game.ball.vx = 0.0
    game.ball.vy = 120.0  # Moving downward
    
    # Store initial state
    initial_bricks = len(game.level.bricks)
    initial_score = game.score
    
    # Perform a tick to trigger collision
    result = game.tick('none')
    
    # Verify the brick was hit and removed
    assert result['bricks_remaining'] == initial_bricks - 1
    assert result['score'] == initial_score + config.points_per_brick
    
    # Verify that the brick was actually removed from the level
    assert game.level.remaining() == initial_bricks - 1


def test_bottom_out_decrements_lives_and_resets_level():
    """Test that a bottom-out decrements lives and resets the level when lives remain."""
    # Create a game with minimal lives for easier testing
    config = GameConfig(
        width=300,
        height=400,
        lives=2,  # Start with 2 lives
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
    
    # Position ball below the screen to trigger bottom-out
    game.ball.x = 150
    game.ball.y = 450  # Below the game area
    game.ball.vx = 0.0
    game.ball.vy = 120.0  # Moving downward
    
    # Store initial state
    initial_lives = game.lives
    initial_bricks = game.level.remaining()
    
    # Perform a tick to trigger bottom-out
    result = game.tick('none')
    
    # Verify lives were decremented
    assert result['lives'] == initial_lives - 1
    assert game.lives == initial_lives - 1
    
    # Verify level was reset (same number of bricks)
    assert result['bricks_remaining'] == initial_bricks
    assert game.level.remaining() == initial_bricks
    
    # Verify game is still running (since lives > 0)
    assert result['status'] == 'running'
    assert game.status == 'running'
    
    # Verify ball was reset to starting position
    assert game.ball.x == config.width / 2
    assert game.ball.y == config.height - 50 - 20
    assert game.ball.vx == 0.0
    assert game.ball.vy == -config.ball_speed