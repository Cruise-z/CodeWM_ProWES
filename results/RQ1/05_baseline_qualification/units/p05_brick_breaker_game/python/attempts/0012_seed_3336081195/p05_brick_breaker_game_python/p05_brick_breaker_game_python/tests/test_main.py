"""Protocol-level tests for the brick breaker game.

This module tests the runtime wiring and core game rules through
deterministic demonstrations and assertions.
"""

import pytest
from Main import Main
from brick_breaker import Game
from brick_breaker.game import Game as GameClass
from brick_breaker.level import make_grid_level
from brick_breaker.config import GameConfig


def test_run_demo_returns_stable_snapshot():
    """Test that Main.run_demo returns a stable snapshot without side effects."""
    # Run the demo multiple times to ensure consistency
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
    
    # Verify consistent values across runs
    assert snapshot1['score'] == snapshot2['score']
    assert snapshot1['lives'] == snapshot2['lives']
    assert snapshot1['status'] == snapshot2['status']
    assert snapshot1['bricks_remaining'] == snapshot2['bricks_remaining']
    
    # Verify ball structure
    assert 'x' in snapshot1['ball']
    assert 'y' in snapshot1['ball']
    assert 'vx' in snapshot1['ball']
    assert 'vy' in snapshot1['ball']
    
    # Verify paddle structure
    assert 'x' in snapshot1['paddle']
    assert 'y' in snapshot1['paddle']


def test_brick_hit_increments_score_and_removes_brick():
    """Test that a ball-brick collision increments score and removes the brick."""
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
    
    # Create a game with one brick
    game = GameClass(config)
    
    # Verify initial state
    assert game.level.remaining() == 1
    assert game.score == 0
    
    # Simulate a ball hitting the brick from below (top of brick)
    # Position ball above the brick so it will collide
    game.ball.x = 25.0  # Center of brick
    game.ball.y = 30.0  # Just above brick
    game.ball.vx = 0.0
    game.ball.vy = 120.0  # Moving downward
    
    # Perform one tick to trigger collision
    snapshot = game.tick('none')
    
    # Verify the brick was hit and removed
    assert game.level.remaining() == 0
    assert game.score == 100  # Points for one brick
    
    # Verify the snapshot reflects the changes
    assert snapshot['bricks_remaining'] == 0
    assert snapshot['score'] == 100


def test_bottom_out_decrements_lives_and_resets_level():
    """Test that a bottom-out decrements lives and resets the level when lives remain."""
    # Create a config with minimal lives for quick testing
    config = GameConfig(
        width=300,
        height=400,
        lives=2,  # Two lives so we can test reset
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
    assert game.lives == 2
    assert game.level.remaining() == 1
    
    # Make the ball go below the screen
    game.ball.y = 420.0  # Below the screen height
    
    # Perform one tick to trigger bottom-out
    snapshot = game.tick('none')
    
    # Verify lives decreased
    assert game.lives == 1
    assert game.status == 'running'  # Should not be game over yet
    
    # Verify level was reset (still has bricks)
    assert game.level.remaining() == 1
    
    # Verify snapshot reflects the changes
    assert snapshot['lives'] == 1
    assert snapshot['status'] == 'running'
    assert snapshot['bricks_remaining'] == 1
    
    # Now let's test game over condition
    # Make another bottom-out
    game.ball.y = 420.0
    snapshot = game.tick('none')
    
    # Verify game over
    assert game.lives == 0
    assert game.status == 'gameover'
    
    # Verify snapshot reflects game over
    assert snapshot['lives'] == 0
    assert snapshot['status'] == 'gameover'