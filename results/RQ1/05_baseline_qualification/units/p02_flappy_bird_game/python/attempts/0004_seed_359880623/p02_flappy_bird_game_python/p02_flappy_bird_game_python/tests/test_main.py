"""Protocol-level tests for the Flappy Bird game implementation."""

from flappy_bird import Game, Pipe, Config
from flappy_bird.scoring import is_pipe_scored


def test_runtime_wiring():
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
    assert status["pipes"] == []
    
    # Perform a single flap to start the game
    game.flap()
    
    # Verify state changed to running
    status = game.status()
    assert status["state"] == "running"
    assert status["vy"] == config.flap_impulse
    
    # Step the game a few times to show physics in action
    for _ in range(5):
        game.step()
    
    # Verify game state after steps
    status = game.status()
    assert status["state"] == "running"
    assert status["tick"] == 5
    assert status["score"] == 0  # No pipes to score yet
    assert status["pipes"] == []  # No pipes spawned yet


def test_scoring_helper_purity():
    """Test the scoring helper function is_pipe_scored with various inputs."""
    # Test case 1: Bird hasn't passed, pipe right edge is to the left -> should score
    result = is_pipe_scored(bird_x=100.0, pipe_right_edge=90.0, already_passed=False)
    assert result is True
    
    # Test case 2: Bird hasn't passed, pipe right edge is to the right -> should not score
    result = is_pipe_scored(bird_x=100.0, pipe_right_edge=110.0, already_passed=False)
    assert result is False
    
    # Test case 3: Bird already passed -> should not score even if pipe is to the left
    result = is_pipe_scored(bird_x=100.0, pipe_right_edge=90.0, already_passed=True)
    assert result is False
    
    # Test case 4: Bird at exact position -> should not score
    result = is_pipe_scored(bird_x=100.0, pipe_right_edge=100.0, already_passed=False)
    assert result is False
    
    # Test case 5: Bird far to the right with pipe far to the left -> should score
    result = is_pipe_scored(bird_x=200.0, pipe_right_edge=100.0, already_passed=False)
    assert result is True


def test_scoring_integration_order():
    """Test that scoring happens in correct order: move pipes, score, then remove."""
    # Create a custom config for predictable behavior
    config = Config(
        bird_x=100.0,
        pipe_speed=10.0,
        gap_height=100.0,
        pipe_width=50.0,
        spawn_interval_ticks=100,
        world_height=500.0,
        world_ceiling=0.0,
        world_floor=500.0,
    )
    
    # Create a game instance with an initial pipe
    pipe = Pipe(x=150.0, gap_y=200.0, width=50.0, gap_height=100.0, passed=False)
    game = Game(config, initial_pipes=[pipe])
    
    # Start the game
    game.flap()
    
    # Step through several ticks to trigger scoring
    # After 5 ticks, pipe should have moved left by 50 units (5 * 10)
    # So pipe x=150 becomes x=100, right edge at x=150
    # Bird is at x=100, so pipe right edge (150) is > bird_x (100), so not scored yet
    for _ in range(5):
        game.step()
    
    # Check status after moving pipes but before scoring
    status = game.status()
    assert len(status["pipes"]) == 1
    assert status["pipes"][0]["x"] == 100.0  # 150 - 5*10
    assert status["pipes"][0]["passed"] is False
    assert status["score"] == 0
    
    # Step one more tick to score the pipe
    # Now pipe is at x=90, right edge at x=140
    # Bird is at x=100, so pipe right edge (140) > bird_x (100), not scored yet
    game.step()
    
    # Step one more tick
    # Pipe at x=80, right edge at x=130
    # Bird at x=100, so pipe right edge (130) > bird_x (100), not scored yet
    game.step()
    
    # Step one more tick
    # Pipe at x=70, right edge at x=120
    # Bird at x=100, so pipe right edge (120) > bird_x (100), not scored yet
    game.step()
    
    # Step one more tick
    # Pipe at x=60, right edge at x=110
    # Bird at x=100, so pipe right edge (110) > bird_x (100), not scored yet
    game.step()
    
    # Step one more tick
    # Pipe at x=50, right edge at x=100
    # Bird at x=100, so pipe right edge (100) = bird_x (100), not scored yet
    game.step()
    
    # Step one more tick
    # Pipe at x=40, right edge at x=90
    # Bird at x=100, so pipe right edge (90) < bird_x (100), should be scored now
    game.step()
    
    # Verify scoring happened correctly
    status = game.status()
    assert len(status["pipes"]) == 1
    assert status["pipes"][0]["x"] == 40.0  # 150 - 11*10
    assert status["pipes"][0]["passed"] is True
    assert status["score"] == 1
    
    # Step a few more ticks to ensure the pipe is removed
    for _ in range(5):
        game.step()
    
    # Verify pipe was removed
    status = game.status()
    assert len(status["pipes"]) == 0
    assert status["score"] == 1