"""Protocol-level tests for the tank battle game."""

from tank_battle import (
    Game,
    Arena,
    Obstacle,
    Rect,
    Tank,
    Projectile,
    ScoreBoard,
    Direction,
    Command,
    MoveForward,
    RotateLeft,
    RotateRight,
    RotateTo,
    Fire,
    build_default_demo,
)
from Main import run_demo


def test_runtime_demo() -> None:
    """Test that run_demo produces the expected snapshot structure."""
    result = run_demo()
    
    # Check that result is a dict with the expected keys
    assert isinstance(result, dict)
    assert set(result.keys()) == {"arena", "tanks", "projectiles", "scores", "winner"}
    
    # Check that p1 direction is S as expected
    assert result["tanks"]["p1"]["direction"] == "S"


def test_obstacle_blocking() -> None:
    """Test that obstacles properly block tank movement."""
    # Create arena with obstacle
    arena = Arena(8, 5, [Obstacle(Rect(3, 1, 1, 1))])
    
    # Create tanks
    p1 = Tank("p1", "P1", 2, 1, Direction.E)
    p2 = Tank("p2", "P2", 6, 4, Direction.W)
    
    # Create game
    game = Game(arena, {"p1": p1, "p2": p2})
    
    # Queue MoveForward(2) for p1 and tick
    game.queue_command("p1", MoveForward(2))
    game.tick()
    
    # Assert p1 remains at (2, 1) due to obstacle
    assert game.tanks["p1"].x == 2
    assert game.tanks["p1"].y == 1


def test_projectile_hit_scoring() -> None:
    """Test projectile same-tick movement and hit scoring."""
    # Create arena
    arena = Arena(8, 5, [])
    
    # Create tanks
    p1 = Tank("p1", "P1", 1, 2, Direction.E)
    p2 = Tank("p2", "P2", 4, 2, Direction.W, 2, 1)
    
    # Create game
    game = Game(arena, {"p1": p1, "p2": p2})
    
    # Queue Fire for p1 and tick once
    game.queue_command("p1", Fire())
    game.tick()
    
    # After tick 1, there should be one projectile at (3, 2)
    assert len(game.projectiles) == 1
    assert game.projectiles[0].x == 3
    assert game.projectiles[0].y == 2
    
    # Tick again - projectile should move to (4, 2) and hit p2
    game.tick()
    
    # Verify p2 health is now 1
    assert game.tanks["p2"].health == 1
    
    # Verify no projectiles remain
    assert len(game.projectiles) == 0
    
    # Verify scoring
    assert game.scores.hits["p1"] == 1
    assert game.scores.kills["p1"] == 0
    assert game.scores.score("p1") == 1
    assert game.winner() is None


def test_reset_fixture() -> None:
    """Test that reset properly restores initial state."""
    # Create fresh game
    arena = Arena(8, 5, [])
    p1 = Tank("p1", "P1", 1, 2, Direction.E)
    p2 = Tank("p2", "P2", 4, 2, Direction.W, 2, 1)
    
    game = Game(arena, {"p1": p1, "p2": p2})
    
    # Immediately capture initial snapshot before any command/tick
    initial = game.snapshot()
    
    # Ensure we didn't queue Fire and didn't tick before capturing initial
    assert len(game.projectiles) == 0
    assert len(game.command_queue) == 0
    assert game.scores.hits == {"p1": 0, "p2": 0}
    assert game.scores.kills == {"p1": 0, "p2": 0}
    
    # Mutate state
    game.queue_command("p1", MoveForward(1))
    game.tick()
    game.tanks["p2"].health = 0  # Simulate a kill
    
    # Reset the game
    game.reset()
    
    # Check that snapshot equals initial
    assert game.snapshot() == initial
    
    # Check that queues are empty
    assert len(game.projectiles) == 0
    assert len(game.command_queue) == 0
    
    # Check that scores are reset
    assert game.scores.hits == {"p1": 0, "p2": 0}
    assert game.scores.kills == {"p1": 0, "p2": 0}
    assert game.scores.score("p1") == 0
    assert game.scores.score("p2") == 0
    
    # Check projectile ID reset
    assert game.next_projectile_id == 0