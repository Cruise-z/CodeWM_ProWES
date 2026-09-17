"""Runtime bootstrap, headless demo for the tank battle game."""

from tank_battle import build_default_demo, RotateRight


def run_demo() -> dict:
    """Run a simple demo of the tank battle game.

    Returns:
        A dictionary snapshot of the game state after one tick.
    """
    # Build the default demo game
    game = build_default_demo()
    
    # Queue a RotateRight command for player 1
    game.queue_command("p1", RotateRight())
    
    # Execute one tick
    game.tick()
    
    # Return the snapshot
    return game.snapshot()


if __name__ == "__main__":
    # Run the demo and print the result
    result = run_demo()
    print(result)