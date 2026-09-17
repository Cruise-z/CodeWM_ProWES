"""Headless demo for the Flappy Bird game.

This script demonstrates the basic usage of the Flappy Bird game engine
by constructing a game, performing a single flap, stepping a few ticks,
and printing a summary of the game state.
"""

from flappy_bird import Game, Pipe, Config


def main():
    """Run a headless demonstration of the Flappy Bird game."""
    # Create a default configuration
    config = Config()
    
    # Create a game instance with the configuration
    game = Game(config)
    
    # Perform a single flap to start the game
    game.flap()
    
    # Step the game a few times to show physics in action
    for _ in range(5):
        game.step()
    
    # Print a summary of the game state
    status = game.status()
    print("Game Status:")
    print(f"  State: {status['state']}")
    print(f"  Tick: {status['tick']}")
    print(f"  Bird Y: {status['y']:.1f}")
    print(f"  Bird Vy: {status['vy']:.1f}")
    print(f"  Score: {status['score']}")
    print(f"  Pipes: {len(status['pipes'])}")


if __name__ == "__main__":
    main()