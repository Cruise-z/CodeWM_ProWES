"""Protocol-level tests for the Flappy Bird implementation.

These tests cover the core game mechanics, scoring logic, and state transitions
without requiring any GUI or I/O operations.
"""

from flappy_bird import Game, Pipe, Config
from flappy_bird.scoring import is_pipe_scored
from flappy_bird.config import Config


def test_runtime_wiring() -> None:
    """Test basic runtime wiring: Config and Game construction, flap, and step."""
    # Create a default configuration
    config = Config()
    
    # Create a game instance with the configuration
    game = Game(config)
    
    # Verify initial state
    status = game.status()
    assert status["state"] == "ready"
    assert status["tick"] == 0
    assert status["y"] == config.start_y
    assert status["vy"] == 0.0
    assert status["score"] == 0
    assert len(status["pipes"]) == 0
    
    # Perform one flap to start the game
    game.flap()
    
    # Verify state transition and initial impulse
    status = game.status()
    assert status["state"] == "running"
    assert status["vy"] == config.flap_impulse
    
    # Step the game a few times to demonstrate physics and scoring
    for i in range(5):
        game.step()
        status = game.status()
        assert status["tick"] == i + 1
        assert status["state"] == "running"
    
    # Verify final status after multiple steps
    status = game.status()
    assert status["state"] == "running"
    assert status["tick"] == 5
    assert status["score"] == 0  # No pipes to score yet


def test_scoring_helper_purity() -> None:
    """Test the scoring helper function is_pipe_scored with various inputs."""
    # Test case 1: Bird is to the right of pipe right edge -> should not score
    result = is_pipe_scored(150.0, 120.0, False)
    assert result is False
    
    # Test case 2: Bird is to the left of pipe right edge, not passed -> should score
    result = is_pipe_scored(100.0, 120.0, False)
    assert result is True
    
    # Test case 3: Bird is to the left of pipe right edge, already passed -> should not score
    result = is_pipe_scored(100.0, 120.0, True)
    assert result is False
    
    # Test case 4: Bird exactly at pipe right edge -> should not score
    result = is_pipe_scored(120.0, 120.0, False)
    assert result is False
    
    # Test case 5: Bird far to the left -> should score
    result = is_pipe_scored(50.0, 100.0, False)
    assert result is True


def test_scoring_integration_order() -> None:
    """Test that scoring happens in the correct order relative to other operations."""
    # Create a custom config with known values for predictable testing
    config = Config(
        bird_x=100.0,
        pipe_speed=3.0,
        pipe_width=50.0,
        gap_height=150.0,
        spawn_interval_ticks=100
    )
    
    # Create a pipe that is initially to the right of the bird
    initial_pipe = Pipe(x=150.0, gap_y=250.0, width=50.0, gap_height=150.0)
    
    # Create game with this pipe
    game = Game(config, [initial_pipe])
    
    # Initially, the pipe should not be scored
    status = game.status()
    assert len(status["pipes"]) == 1
    assert status["pipes"][0]["passed"] is False
    assert status["score"] == 0
    
    # Perform flap to start game
    game.flap()
    
    # Step once to move pipe toward bird
    game.step()
    
    # Pipe should still not be scored since it's to the right of the bird
    status = game.status()
    assert status["pipes"][0]["passed"] is False
    assert status["score"] == 0
    
    # Step more times to move pipe to the left of bird
    for _ in range(10):
        game.step()
    
    # Now pipe should be scored
    status = game.status()
    assert status["pipes"][0]["passed"] is True
    assert status["score"] == 1
    
    # Step further to make sure pipe is removed
    for _ in range(20):
        game.step()
    
    # Pipe should be removed now
    status = game.status()
    assert len(status["pipes"]) == 0
    assert status["score"] == 1


def test_flap_semantics_and_physics_order() -> None:
    """Test flap semantics and physics integration order."""
    config = Config(
        gravity=0.5,
        flap_impulse=-7.5,
        max_vy=10.0,
        start_y=250.0
    )
    
    game = Game(config)
    
    # Test initial state
    status = game.status()
    assert status["state"] == "ready"
    assert status["vy"] == 0.0
    assert status["y"] == 250.0
    
    # Flap from ready state should transition to running and apply impulse
    game.flap()
    status = game.status()
    assert status["state"] == "running"
    assert status["vy"] == -7.5  # Immediate flap impulse applied
    
    # Step once to see physics in action
    game.step()
    status = game.status()
    assert status["state"] == "running"
    # Should have integrated gravity: vy = -7.5 + 0.5 = -7.0
    assert status["vy"] == -7.0
    # Should have updated position: y = 250.0 + (-7.0) = 243.0
    assert status["y"] == 243.0
    assert status["tick"] == 1


def test_collision_detection() -> None:
    """Test collision detection with bounds and pipes."""
    config = Config(
        world_ceiling=0.0,
        world_floor=500.0,
        start_y=250.0
    )
    
    game = Game(config)
    
    # Flap to start
    game.flap()
    
    # Step several times to go below floor
    for _ in range(200):
        game.step()
        status = game.status()
        if status["state"] == "game_over":
            break
    
    # Game should be over due to floor collision
    assert game.status()["state"] == "game_over"


def test_pipe_lifecycle() -> None:
    """Test pipe lifecycle: creation, movement, scoring, and removal."""
    config = Config(
        bird_x=100.0,
        pipe_speed=3.0,
        pipe_width=50.0,
        gap_height=150.0,
        spawn_interval_ticks=100
    )
    
    # Create a pipe that will trigger scoring
    pipe = Pipe(x=150.0, gap_y=250.0, width=50.0, gap_height=150.0)
    game = Game(config, [pipe])
    
    # Start game
    game.flap()
    
    # Move pipe to the point where it should be scored
    for _ in range(20):
        game.step()
    
    # Check that pipe was scored
    status = game.status()
    assert len(status["pipes"]) == 1
    assert status["pipes"][0]["passed"] is True
    assert status["score"] == 1
    
    # Continue stepping until pipe is off screen
    for _ in range(50):
        game.step()
    
    # Pipe should be removed now
    status = game.status()
    assert len(status["pipes"]) == 0
    assert status["score"] == 1