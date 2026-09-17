"""Protocol-level tests for the brick breaker game.

These tests verify the runtime wiring and core game rules:
- Main.run_demo returns a stable snapshot without side effects
- A ball-brick collision increments score and removes the brick at zero durability
- A bottom-out decrements lives and resets the level when lives remain
"""

import pytest
from Main import Main
from brick_breaker import Game, GameConfig
from brick_breaker.game import Game as GameClass
from brick_breaker.level import make_grid_level
from brick_breaker.config import GameConfig as GameConfigClass


def test_main_run_demo_returns_stable_snapshot():
    """Test that Main.run_demo returns a consistent snapshot without side effects."""
    # Run the demo multiple times to ensure consistency
    snapshot1 = Main.run_demo()
    snapshot2 = Main.run_demo()
    
    # Verify the snapshot structure
    assert isinstance(snapshot1, dict)
    assert 'score' in snapshot1
    assert 'lives' in snapshot1
    assert 'status' in snapshot1
    assert 'bricks_remaining' in snapshot1
    assert 'ball' in snapshot1
    assert 'paddle' in snapshot1
    
    # Verify the snapshot values are correct types
    assert isinstance(snapshot1['score'], int)
    assert isinstance(snapshot1['lives'], int)
    assert isinstance(snapshot1['status'], str)
    assert isinstance(snapshot1['bricks_remaining'], int)
    assert isinstance(snapshot1['ball'], dict)
    assert isinstance(snapshot1['paddle'], dict)
    
    # Verify ball properties
    ball = snapshot1['ball']
    assert 'x' in ball
    assert 'y' in ball
    assert 'vx' in ball
    assert 'vy' in ball
    assert isinstance(ball['x'], float)
    assert isinstance(ball['y'], float)
    assert isinstance(ball['vx'], float)
    assert isinstance(ball['vy'], float)
    
    # Verify paddle properties
    paddle = snapshot1['paddle']
    assert 'x' in paddle
    assert 'y' in paddle
    assert isinstance(paddle['x'], float)
    assert isinstance(paddle['y'], float)
    
    # Verify snapshots are identical
    assert snapshot1 == snapshot2


def test_ball_brick_collision_increments_score_and_removes_brick():
    """Test that a ball-brick collision increments score and removes brick at zero durability."""
    # Create a custom config with fewer bricks for easier testing
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
    
    # Create a game instance with our config
    game = GameClass(config)
    
    # Verify initial state
    initial_snapshot = game.tick('none')
    assert initial_snapshot['bricks_remaining'] == 1
    assert initial_snapshot['score'] == 0
    
    # Manually set ball position to collide with the brick
    # Place ball just above the brick so it will hit it on next tick
    game.ball.x = 75.0  # Center of brick
    game.ball.y = 50.0  # Just above brick
    game.ball.vx = 0.0
    game.ball.vy = 120.0  # Moving downward
    
    # Perform a tick to trigger collision
    snapshot_after_collision = game.tick('none')
    
    # Verify brick was removed and score increased
    assert snapshot_after_collision['bricks_remaining'] == 0
    assert snapshot_after_collision['score'] == 100  # points_per_brick


def test_bottom_out_decrements_lives_and_resets_level():
    """Test that a bottom-out decrements lives and resets the level when lives remain."""
    # Create a custom config with fewer lives for easier testing
    config = GameConfigClass(
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
    
    # Create a game instance with our config
    game = GameClass(config)
    
    # Verify initial state
    initial_snapshot = game.tick('none')
    assert initial_snapshot['lives'] == 2
    
    # Manually set ball position to cause bottom-out
    # Place ball below the screen
    game.ball.x = 150.0
    game.ball.y = 450.0  # Below the screen
    game.ball.vx = 0.0
    game.ball.vy = 120.0  # Moving downward
    
    # Perform a tick to trigger bottom-out
    snapshot_after_bottom_out = game.tick('none')
    
    # Verify lives were decremented
    assert snapshot_after_bottom_out['lives'] == 1
    
    # Verify level was reset (should still have 1 brick)
    assert snapshot_after_bottom_out['bricks_remaining'] == 1
    
    # Verify game is still running (since lives > 0)
    assert snapshot_after_bottom_out['status'] == 'running'
    
    # Verify ball position was reset
    assert snapshot_after_bottom_out['ball']['x'] == 150.0
    assert snapshot_after_bottom_out['ball']['y'] == 380.0  # Above paddle
    
    # Verify paddle position was reset
    assert snapshot_after_bottom_out['paddle']['x'] == 150.0
    assert snapshot_after_bottom_out['paddle']['y'] == 380.0  # Bottom center