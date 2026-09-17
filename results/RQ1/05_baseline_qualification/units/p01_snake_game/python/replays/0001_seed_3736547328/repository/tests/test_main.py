"""Test suite for the snake game implementation."""

from snake_game import Direction, Position, Grid, Game, RandomProvider


def test_no_growth_step() -> None:
    """Test a single step with no food consumption."""
    # Create deterministic random provider with known food position
    food_sequence = [Position(1, 1)]
    rng = RandomProvider(sequence=food_sequence)
    
    # Create game with deterministic settings
    grid = Grid(10, 10)
    start_pos = Position(5, 5)
    initial_direction = Direction.RIGHT
    
    game = Game(grid, rng, start_pos, initial_direction)
    
    # Perform one step
    game.step()
    
    # Validate state matches expected values
    state = game.state()
    
    # Check flat state schema
    expected_keys = {"width", "height", "snake", "food", "score", "over", "direction"}
    actual_keys = set(state.keys())
    assert actual_keys == expected_keys, f"State keys mismatch: expected {expected_keys}, got {actual_keys}"
    
    # Check specific values
    assert state["width"] == 10
    assert state["height"] == 10
    assert state["snake"] == [(6, 5)]  # Head moved right from (5,5) to (6,5)
    assert state["food"] == (1, 1)     # Food unchanged
    assert state["score"] == 0         # No food eaten
    assert state["over"] == False      # Game not over
    assert state["direction"] == "RIGHT"


def test_growth_step() -> None:
    """Test a single step with food consumption."""
    # Create deterministic random provider with known food positions
    food_sequence = [Position(6, 5), Position(1, 1)]  # First food at (6,5) to eat, then new food at (1,1)
    rng = RandomProvider(sequence=food_sequence)
    
    # Create game with deterministic settings
    grid = Grid(10, 10)
    start_pos = Position(5, 5)
    initial_direction = Direction.RIGHT
    
    game = Game(grid, rng, start_pos, initial_direction)
    
    # Perform one step (should eat the food at (6,5))
    game.step()
    
    # Validate state matches expected values
    state = game.state()
    
    # Check flat state schema
    expected_keys = {"width", "height", "snake", "food", "score", "over", "direction"}
    actual_keys = set(state.keys())
    assert actual_keys == expected_keys, f"State keys mismatch: expected {expected_keys}, got {actual_keys}"
    
    # Check specific values
    assert state["width"] == 10
    assert state["height"] == 10
    assert state["snake"] == [(6, 5), (5, 5)]  # Head at (6,5) and body at (5,5) - grew by 1
    assert state["food"] == (1, 1)             # New food placed at (1,1)
    assert state["score"] == 1                 # Score incremented
    assert state["over"] == False              # Game not over
    assert state["direction"] == "RIGHT"