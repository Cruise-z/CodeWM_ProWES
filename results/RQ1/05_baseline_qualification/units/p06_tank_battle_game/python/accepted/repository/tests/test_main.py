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


def test_runtime_demo():
    """Test the runtime demo functionality."""
    result = run_demo()
    
    # Check that result is a dict with expected keys
    assert isinstance(result, dict)
    assert set(result.keys()) == {"arena", "tanks", "projectiles", "scores", "winner"}
    
    # Check that p1 direction is S after RotateRight from E
    assert result["tanks"]["p1"]["direction"] == "S"


def test_obstacle_blocking():
    """Test that obstacles properly block tank movement."""
    # Create arena with obstacle
    arena = Arena(8, 5, [Obstacle(Rect(3, 1, 1, 1))])
    
    # Create tanks
    p1 = Tank("p1", "P1", 2, 1, Direction.E)
    p2 = Tank("p2", "P2", 6, 4, Direction.W)
    tanks = {"p1": p1, "p2": p2}
    
    # Create game
    game = Game(arena, tanks)
    
    # Queue MoveForward(2) for p1
    game.queue_command("p1", MoveForward(2))
    
    # Tick
    game.tick()
    
    # Assert p1 remains at (2, 1) due to obstacle at (3, 1)
    assert game.tanks["p1"].x == 2
    assert game.tanks["p1"].y == 1


def test_projectile_hit_scoring():
    """Test projectile hit and scoring behavior."""
    # Create arena
    arena = Arena(8, 5, [])
    
    # Create tanks
    p1 = Tank("p1", "P1", 1, 2, Direction.E)
    p2 = Tank("p2", "P2", 4, 2, Direction.W, 2, 1)
    tanks = {"p1": p1, "p2": p2}
    
    # Create game
    game = Game(arena, tanks)
    
    # Queue Fire for p1
    game.queue_command("p1", Fire())
    
    # Tick once - should create projectile at (3, 2)
    game.tick()
    
    # Check projectile exists at correct position
    assert len(game.projectiles) == 1
    assert game.projectiles[0].x == 3
    assert game.projectiles[0].y == 2
    
    # Tick again - projectile should move to (4, 2) and hit p2
    game.tick()
    
    # Check p2 has taken damage
    assert game.tanks["p2"].health == 1
    
    # Check no projectiles remain
    assert len(game.projectiles) == 0
    
    # Check scoring
    assert game.scores.hits["p1"] == 1
    assert game.scores.kills["p1"] == 0
    assert game.scores.score("p1") == 1
    
    # Check winner is None since p2 is still alive
    assert game.winner() is None


def test_reset_fixture():
    """Test that reset correctly restores initial state."""
    # Create fresh game
    arena = Arena(8, 5, [])
    p1 = Tank("p1", "P1", 1, 2, Direction.E)
    p2 = Tank("p2", "P2", 4, 2, Direction.W, 2, 1)
    tanks = {"p1": p1, "p2": p2}
    game = Game(arena, tanks)
    
    # Immediately capture initial state
    initial = game.snapshot()
    
    # Mutate state
    game.queue_command("p1", MoveForward(1))
    game.tick()
    game.tanks["p2"].health = 0
    
    # Reset
    game.reset()
    
    # Check state matches initial
    assert game.snapshot() == initial
    
    # Check projectiles and command queue are empty
    assert len(game.projectiles) == 0
    assert len(game.command_queue) == 0
    
    # Check scores are reset
    assert game.scores.hits == {"p1": 0, "p2": 0}
    assert game.scores.kills == {"p1": 0, "p2": 0}
    assert game.scores.score("p1") == 0
    assert game.scores.score("p2") == 0
    
    # Check next_projectile_id is reset
    assert game.next_projectile_id == 0