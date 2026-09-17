"""Protocol-level tests for the Flappy Bird implementation."""

from flappy_bird import Game, Pipe, Config
from flappy_bird.scoring import is_pipe_scored
from flappy_bird.config import Config


def test_runtime_wiring() -> None:
    """Test basic runtime wiring: Config and Game construction, flap, and step."""
    # Create a default configuration
    config = Config.default()
    
    # Create a game instance
    game = Game(config)
    
    # Verify initial state
    status = game.status()
    assert status["state"] == "ready"
    assert status["tick"] == 0
    assert status["y"] == config.start_y
    assert status["vy"] == 0.0
    assert status["score"] == 0
    assert status["pipes"] == []
    
    # Perform one flap to start the game
    game.flap()
    
    # Verify state transition
    status = game.status()
    assert status["state"] == "running"
    assert status["vy"] == config.flap_impulse  # Should have immediate impulse
    
    # Step the game a few times
    for _ in range(3):
        game.step()
    
    # Verify game progression
    status = game.status()
    assert status["tick"] == 4  # 1 initial + 3 steps
    assert status["state"] == "running"
    assert status["y"] < config.start_y  # Should have moved down due to gravity
    assert status["vy"] < 0.0  # Should be moving downward
    assert status["score"] == 0  # No pipes to score yet


def test_scoring_helper_purity() -> None:
    """Test the scoring helper's purity and strict-left rule."""
    # Test case 1: Bird hasn't passed pipe, pipe is to the right -> should score
    assert is_pipe_scored(100.0, 90.0, False) is True
    
    # Test case 2: Bird hasn't passed pipe, pipe is to the left -> should not score
    assert is_pipe_scored(100.0, 110.0, False) is False
    
    # Test case 3: Bird already passed pipe -> should not score even if pipe is to the right
    assert is_pipe_scored(100.0, 90.0, True) is False
    
    # Test case 4: Bird at exact same position -> should not score
    assert is_pipe_scored(100.0, 100.0, False) is False
    
    # Test case 5: Edge case - very close positions
    assert is_pipe_scored(100.0001, 100.0, False) is True
    assert is_pipe_scored(99.9999, 100.0, False) is False


def test_scoring_integration_order() -> None:
    """Test scoring integration order: move pipes, score, then remove off-screen."""
    config = Config.default()
    
    # Create a game with a pipe that will be scored
    pipe = Pipe(x=80.0, gap_y=200.0, width=config.pipe_width, gap_height=config.gap_height)
    game = Game(config, [pipe])
    
    # Start the game
    game.flap()
    
    # Step until bird passes the pipe (bird_x=100, pipe.right_edge=130)
    # So we need bird_x to go from 100 to > 130
    # Bird starts at 250, falls due to gravity
    # With gravity=0.5, max_vy=10, flap_impulse=-7.5
    # Step 1: vy = integrate_vy(0, 0.5, 10) = 0.5, y = 250 + 0.5 = 250.5
    # Step 2: vy = integrate_vy(0.5, 0.5, 10) = 1.0, y = 250.5 + 1.0 = 251.5
    # ...
    # After ~15 steps, bird should cross pipe
    for _ in range(20):
        game.step()
    
    # Verify scoring happened correctly
    status = game.status()
    assert status["score"] == 1
    assert len(status["pipes"]) == 1  # Pipe still present because it's not off-screen yet
    assert status["pipes"][0]["passed"] is True
    
    # Now let the pipe move off-screen
    # Pipe starts at x=80, width=50, so right edge at 130
    # Need to move pipe until right edge < 0 (i.e., x < -50)
    # At pipe_speed=3.0, needs about 44 steps to move pipe completely off-screen
    # But we want to test that pipe gets removed after scoring
    # Let's step more to make sure pipe moves off-screen
    for _ in range(50):
        game.step()
    
    # Verify pipe is now gone
    status = game.status()
    assert status["score"] == 1  # Score shouldn't change anymore
    assert len(status["pipes"]) == 0  # No pipes remain