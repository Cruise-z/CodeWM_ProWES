"""Runtime entry point for the snake game demo."""

from snake_game import Direction, Position, Grid, Game, RandomProvider


def main() -> None:
    """Run a deterministic snake game demo."""
    # Create a deterministic random provider with known food positions
    food_sequence = [Position(1, 1)]
    rng = RandomProvider(sequence=food_sequence)
    
    # Create game with deterministic settings
    grid = Grid(10, 10)
    start_pos = Position(5, 5)
    initial_direction = Direction.RIGHT
    
    game = Game(grid, rng, start_pos, initial_direction)
    
    # Perform at most two safe steps
    game.step()
    game.step()
    
    # Print one snapshot of the game state
    state = game.state()
    print(state)


if __name__ == "__main__":
    main()