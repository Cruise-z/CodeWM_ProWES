"""Protocol-level tests for the Flappy Bird game implementation.

Tests cover:
- Runtime wiring: Config and Game construction
- Game semantics: flap(), step() order, state transitions
- Pure scoring helper: is_pipe_scored behavior
- Scoring integration: strict-left rule, single-pass guarantee
"""

from flappy_bird import Game, Pipe, Config
from flappy_bird.scoring import is_pipe_scored


def test_runtime_wiring() -> None:
    """Test basic runtime wiring: Config and Game creation, flap, and step."""
    # Create config
    config = Config()
    
    # Create game
    game = Game(config)
    
    # Verify initial state
    status = game.status()
    assert status["state"] == "ready"
    assert status["tick"] == 0
    assert status["y"] == config.start_y
    assert status["vy"] == 0.0
    assert status["score"] == 0
    assert status["pipes"] == []
    
    # Perform flap
    game.flap()
    
    # Verify state transition and impulse application
    status = game.status()
    assert status["state"] == "running"
    assert status["vy"] == config.flap_impulse  # Should be -7.5
    
    # Step a few times
    for _ in range(3):
        game.step()
    
    # Verify progression
    status = game.status()
    assert status["tick"] == 3
    assert status["y"] < config.start_y  # Bird should be falling
    assert status["vy"] < 0.0  # Vertical velocity should be negative
    assert status["score"] == 0  # No pipes to score yet


def test_scoring_helper_purity() -> None:
    """Test the scoring helper is_pipe_scored with various inputs."""
    # Test case 1: Not passed, right edge left of bird -> should score
    assert is_pipe_scored(100.0, 90.0, False) is True
    
    # Test case 2: Not passed, right edge right of bird -> should not score
    assert is_pipe_scored(100.0, 110.0, False) is False
    
    # Test case 3: Not passed, right edge equal to bird -> should not score
    assert is_pipe_scored(100.0, 100.0, False) is False
    
    # Test case 4: Already passed -> should not score even if left
    assert is_pipe_scored(100.0, 90.0, True) is False
    
    # Test case 5: Edge case - very close positions
    assert is_pipe_scored(10.0, 9.9, False) is True
    assert is_pipe_scored(10.0, 10.0, False) is False
    assert is_pipe_scored(10.0, 10.1, False) is False


def test_scoring_integration() -> None:
    """Test scoring integration: strict-left rule and single-pass guarantee."""
    config = Config()
    
    # Create a pipe that will be scored
    pipe = Pipe(x=80.0, gap_y=100.0, width=config.pipe_width, gap_height=config.gap_height)
    
    # Create game with the pipe
    game = Game(config, [pipe])
    
    # Start the game
    game.flap()
    
    # Step until bird passes the pipe
    # Bird starts at x=100, pipe starts at x=80, width=50 => right edge at 130
    # Bird needs to move left past x=130 to trigger scoring
    for _ in range(10):
        game.step()
    
    # Check that pipe was scored
    status = game.status()
    assert status["score"] == 1
    assert len(status["pipes"]) == 1
    assert status["pipes"][0]["passed"] is True
    
    # Step more to ensure no duplicate scoring
    for _ in range(5):
        game.step()
    
    # Score should remain 1
    status = game.status()
    assert status["score"] == 1
    assert status["pipes"][0]["passed"] is True
    
    # Advance until pipe goes off screen
    while status["pipes"]:
        game.step()
        status = game.status()
    
    # Score should still be 1, no pipes left
    status = game.status()
    assert status["score"] == 1
    assert status["pipes"] == []


def test_collision_detection() -> None:
    """Test collision detection logic with boundary and pipe collisions."""
    config = Config()
    
    # Test boundary collision (falling off floor)
    game = Game(config)
    game.flap()
    
    # Move bird down to hit floor
    for _ in range(100):
        game.step()
    
    # Should be game over
    assert game.status()["state"] == "game_over"
    
    # Reset
    game.reset()
    
    # Test pipe collision
    # Create a pipe that will collide with bird
    pipe = Pipe(x=config.bird_x, gap_y=200.0, width=config.pipe_width, gap_height=config.gap_height)
    game = Game(config, [pipe])
    
    # Start the game
    game.flap()
    
    # Step until bird collides with pipe
    for _ in range(10):
        game.step()
    
    # Should be game over due to collision
    assert game.status()["state"] == "game_over"


def test_game_state_transitions() -> None:
    """Test correct handling of game state transitions."""
    config = Config()
    game = Game(config)
    
    # Initial state should be 'ready'
    assert game.status()["state"] == "ready"
    
    # Flap from ready should transition to running
    game.flap()
    assert game.status()["state"] == "running"
    
    # Flap from running should stay running
    game.flap()
    assert game.status()["state"] == "running"
    
    # Game over state should not respond to flap
    game.reset()
    game.flap()
    game.step()  # Make it game over
    game.status()["state"] = "game_over"  # Manually set to game over
    game.flap()  # Should not change state
    assert game.status()["state"] == "game_over"


def test_physics_order() -> None:
    """Test that physics integration order is maintained."""
    config = Config()
    game = Game(config)
    game.flap()
    
    # Get initial values
    initial_status = game.status()
    initial_y = initial_status["y"]
    initial_vy = initial_status["vy"]
    
    # Step once
    game.step()
    status = game.status()
    
    # Verify physics order:
    # 1. vy updated with gravity
    # 2. y updated with new vy
    assert abs(status["vy"] - (initial_vy + config.gravity)) < 1e-10  # Gravity applied
    assert abs(status["y"] - (initial_y + status["vy"])) < 1e-10  # Position updated with new vy
    
    # Verify no score from early movement
    assert status["score"] == 0
    assert status["tick"] == 1


def test_pipe_movement_and_removal() -> None:
    """Test pipe horizontal movement and removal after scoring."""
    config = Config()
    
    # Create a pipe that will be scored and removed
    pipe = Pipe(x=100.0, gap_y=100.0, width=config.pipe_width, gap_height=config.gap_height)
    game = Game(config, [pipe])
    
    game.flap()
    
    # Step until pipe moves off screen
    # Bird x is 100, pipe starts at 100, width 50 => right edge at 150
    # Move pipe left by pipe_speed * ticks until it disappears
    while pipe.right_edge() >= 0:
        game.step()
        # Update pipe reference
        pipe = game.pipes_readonly()[0] if game.pipes_readonly() else None
    
    # Validate pipe removed
    assert len(game.pipes_readonly()) == 0