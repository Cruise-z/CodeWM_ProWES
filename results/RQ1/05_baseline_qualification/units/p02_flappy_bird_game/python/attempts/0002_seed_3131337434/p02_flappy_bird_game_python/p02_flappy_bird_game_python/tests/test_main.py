"""Protocol-level tests for the Flappy Bird game implementation."""

from flappy_bird import Game, Pipe, Config
from flappy_bird.scoring import is_pipe_scored


def test_runtime_wiring():
    """Test basic runtime wiring: Config and Game construction, flap, and step."""
    # Create a default configuration
    config = Config()
    
    # Create a game instance
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
    
    # Verify state transition and impulse application
    status = game.status()
    assert status["state"] == "running"
    assert status["vy"] == config.flap_impulse
    
    # Step the game a few times
    for _ in range(3):
        game.step()
    
    # Verify game progression
    status = game.status()
    assert status["tick"] == 3
    assert status["state"] == "running"
    assert status["y"] != config.start_y  # Bird should have moved
    assert status["vy"] != config.flap_impulse  # Velocity should have changed due to gravity


def test_scoring_helper_purity():
    """Test the scoring helper function is_pipe_scored with various inputs."""
    # Test case 1: Bird hasn't passed pipe yet, and pipe is to the left
    result = is_pipe_scored(bird_x=150.0, pipe_right_edge=100.0, already_passed=False)
    assert result is True
    
    # Test case 2: Bird has already passed the pipe
    result = is_pipe_scored(bird_x=150.0, pipe_right_edge=100.0, already_passed=True)
    assert result is False
    
    # Test case 3: Bird hasn't passed but pipe is to the right (should not score)
    result = is_pipe_scored(bird_x=150.0, pipe_right_edge=200.0, already_passed=False)
    assert result is False
    
    # Test case 4: Bird exactly at pipe right edge (should not score due to strict left rule)
    result = is_pipe_scored(bird_x=150.0, pipe_right_edge=150.0, already_passed=False)
    assert result is False
    
    # Test case 5: Bird slightly to the left of pipe right edge (should score)
    result = is_pipe_scored(bird_x=150.1, pipe_right_edge=150.0, already_passed=False)
    assert result is True


def test_scoring_integration_order():
    """Test that scoring happens in the correct order relative to other operations."""
    # Create a custom config for predictable behavior
    config = Config(
        bird_x=100.0,
        pipe_speed=5.0,
        pipe_width=50.0,
        gap_height=100.0
    )
    
    # Create a pipe that is just to the right of the bird
    pipe = Pipe(x=50.0, gap_y=300.0, width=config.pipe_width, gap_height=config.gap_height)
    
    # Create a game with this pipe
    game = Game(config, [pipe])
    
    # Initially, pipe should not be scored
    status = game.status()
    assert status["pipes"][0]["passed"] is False
    assert status["score"] == 0
    
    # Flap to start the game
    game.flap()
    
    # Step once - pipe should be scored since bird_x (100) > pipe_right_edge (100) is false
    # But pipe moves left, so right edge becomes 50 + 50 - 5 = 95, bird_x = 100
    # So bird_x > pipe_right_edge (95) is true, pipe should be scored
    game.step()
    
    # Verify scoring happened
    status = game.status()
    assert status["score"] == 1
    assert status["pipes"][0]["passed"] is True
    
    # Step again - pipe should remain scored and not be scored again
    game.step()
    
    status = game.status()
    assert status["score"] == 1  # Should not increase
    assert status["pipes"][0]["passed"] is True  # Should remain passed
    
    # Step more times until pipe goes off screen
    for _ in range(10):
        game.step()
    
    # Pipe should now be removed
    status = game.status()
    assert len(status["pipes"]) == 0  # Pipe should be gone


def test_collision_detection():
    """Test that collision detection works correctly."""
    # Create a config with minimal world boundaries for testing
    config = Config(
        world_height=600.0,
        world_ceiling=0.0,
        world_floor=550.0,
        start_y=200.0,
        bird_x=100.0
    )
    
    # Create a game
    game = Game(config)
    
    # Start the game
    game.flap()
    
    # Step several times so bird falls
    for _ in range(10):
        game.step()
    
    # Bird should be in falling state and eventually hit the ground
    status = game.status()
    assert status["state"] == "game_over" or status["y"] > config.world_floor
    
    # Reset and create a pipe that will cause collision
    game.reset()
    game.flap()
    
    # Create a pipe that intersects with the bird's vertical position
    pipe = Pipe(
        x=config.bird_x - 10,  # Right in front of bird
        gap_y=config.start_y,  # Centered vertically
        width=30.0,
        gap_height=100.0
    )
    
    # Add the pipe to the game
    game._pipes.append(pipe)
    
    # Step until collision should occur
    for _ in range(5):
        game.step()
    
    # Bird should be in game over state due to collision
    status = game.status()
    assert status["state"] == "game_over"


def test_flap_semantics():
    """Test flap semantics: state transitions and impulse application."""
    config = Config()
    game = Game(config)
    
    # Test flap when game is ready
    game.flap()
    status = game.status()
    assert status["state"] == "running"
    assert status["vy"] == config.flap_impulse
    
    # Test flap when game is running (should reapply impulse)
    game.flap()
    status = game.status()
    assert status["state"] == "running"
    assert status["vy"] == config.flap_impulse
    
    # Test flap when game is over (should do nothing)
    game._state = "game_over"
    original_vy = game._bird_vy
    game.flap()
    status = game.status()
    assert status["state"] == "game_over"
    assert status["vy"] == original_vy  # Should not change


def test_game_reset():
    """Test that game reset restores initial state."""
    config = Config()
    game = Game(config)
    
    # Modify game state
    game.flap()
    game.step()
    game.step()
    
    # Check that game has progressed
    status = game.status()
    assert status["state"] == "running"
    assert status["tick"] > 0
    assert status["score"] == 0  # No scoring in test
    
    # Reset game
    game.reset()
    
    # Verify reset state
    status = game.status()
    assert status["state"] == "ready"
    assert status["tick"] == 0
    assert status["y"] == config.start_y
    assert status["vy"] == 0.0
    assert status["score"] == 0
    assert len(status["pipes"]) == 0