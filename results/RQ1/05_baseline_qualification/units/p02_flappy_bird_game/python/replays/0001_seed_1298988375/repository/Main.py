"""Headless demo entry point for the Flappy Bird game.

This script demonstrates the basic usage of the Flappy Bird game engine
by creating a game instance, performing one flap, stepping a few ticks,
and printing the final status.
"""

from flappy_bird import Game, Pipe, Config


def main() -> None:
    """Run a simple headless demonstration of the Flappy Bird game."""
    # Create a default configuration
    config = Config()
    
    # Create a game instance with the configuration
    game = Game(config)
    
    # Perform one flap to start the game
    game.flap()
    
    # Step the game a few times to show physics in action
    for _ in range(5):
        game.step()
    
    # Print the final status
    status = game.status()
    print("Final game status:")
    print(f"  State: {status['state']}")
    print(f"  Tick: {status['tick']}")
    print(f"  Bird Y: {status['y']:.1f}")
    print(f"  Bird VY: {status['vy']:.1f}")
    print(f"  Score: {status['score']}")
    print(f"  Pipes: {len(status['pipes'])}")


if __name__ == "__main__":
    main()