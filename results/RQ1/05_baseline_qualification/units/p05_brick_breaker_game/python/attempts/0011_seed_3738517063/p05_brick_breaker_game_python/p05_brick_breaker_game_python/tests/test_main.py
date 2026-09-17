"""Test suite for the brick breaker game protocol and core rules.

This module contains protocol-level tests that verify:
1. Runtime wiring via Main.run_demo returns a stable snapshot
2. Core game rules work correctly:
   - Brick hits increment score and remove bricks at zero durability
   - Bottom-out decrements lives and resets level when lives remain
"""

from Main import Main
from brick_breaker import Game
from brick_breaker.game import Game as GameClass
from brick_breaker.level import make_grid_level
from brick_breaker.config import GameConfig


def test_run_demo_returns_stable_snapshot():
    """Test that Main.run_demo returns a consistent snapshot without side effects."""
    # Run demo multiple times to ensure determinism
    snapshot1 = Main.run_demo()
    snapshot2 = Main.run_demo()
    
    # Verify basic structure
    assert 'score' in snapshot1
    assert 'lives' in snapshot1
    assert 'status' in snapshot1
    assert 'bricks_remaining' in snapshot1
    assert 'ball' in snapshot1
    assert 'paddle' in snapshot1
    
    # Verify consistency
    assert snapshot1 == snapshot2
    
    # Verify expected initial values
    assert snapshot1['score'] == 0
    assert snapshot1['lives'] == 3
    assert snapshot1['status'] == 'running'
    assert snapshot1['bricks_remaining'] == 15  # 3 rows * 5 cols


def test_ball_brick_collision_increments_score_and_removes_brick():
    """Test that a ball-brick collision increments score and removes brick at zero durability."""
    # Create a game with a single brick at a known position
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
    game = GameClass(config)
    
    # Move ball to hit the brick
    # Position ball so it hits the brick
    game.ball.x = 25.0  # Center of brick
    game.ball.y = 47.0  # Just above brick
    game.ball.vx = 0.0
    game.ball.vy = 120.0  # Moving down
    
    # Perform one tick to trigger collision
    snapshot = game.tick('none')
    
    # Verify brick was hit and removed
    assert snapshot['score'] == 100
    assert snapshot['bricks_remaining'] == 0
    
    # Verify ball bounced
    assert snapshot['ball']['vy'] < 0  # Should be moving up now


def test_bottom_out_decrements_lives_and_resets_level():
    """Test that bottom-out decrements lives and resets level when lives remain."""
    # Create a game with minimal settings for testing
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
    game = GameClass(config)
    
    # Move ball below the screen to trigger bottom-out
    game.ball.y = 450.0  # Below the screen
    game.ball.vx = 0.0
    game.ball.vy = 120.0  # Moving down
    
    # Perform one tick to trigger bottom-out
    snapshot = game.tick('none')
    
    # Verify lives decremented
    assert snapshot['lives'] == 2
    
    # Verify level was reset (same brick count)
    assert snapshot['bricks_remaining'] == 1
    
    # Verify ball was reset
    assert snapshot['ball']['y'] == 380.0  # Slightly above paddle
    assert snapshot['ball']['vy'] < 0  # Should be moving up
    
    # Verify paddle was reset
    assert snapshot['paddle']['x'] == 150.0  # Center of screen


def test_bottom_out_game_over():
    """Test that bottom-out results in game over when no lives remain."""
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
    
    # Create a game instance
    game = GameClass(config)
    
    # Move ball below the screen to trigger bottom-out
    game.ball.y = 450.0  # Below the screen
    game.ball.vx = 0.0
    game.ball.vy = 120.0  # Moving down
    
    # Perform one tick to trigger bottom-out
    snapshot = game.tick('none')
    
    # Verify game over
    assert snapshot['lives'] == 0
    assert snapshot['status'] == 'gameover'
    
    # Verify ball position was reset (should be at paddle level)
    assert snapshot['ball']['y'] == 380.0  # Slightly above paddle
    assert snapshot['ball']['vy'] < 0  # Should be moving up