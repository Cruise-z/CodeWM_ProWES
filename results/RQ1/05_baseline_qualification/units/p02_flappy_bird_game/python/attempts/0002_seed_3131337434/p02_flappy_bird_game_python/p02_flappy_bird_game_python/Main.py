"""Headless demo entry point for the Flappy Bird game."""

from flappy_bird import Game, Pipe, Config

def main():
    """Run a short demo of the Flappy Bird game."""
    # Create a default configuration
    config = Config()
    
    # Create a game instance
    game = Game(config)
    
    # Perform one flap to start the game
    game.flap()
    
    # Step the game a few times
    for _ in range(5):
        game.step()
    
    # Print the final status
    status = game.status()
    print("Game Status:")
    print(f"  State: {status['state']}")
    print(f"  Tick: {status['tick']}")
    print(f"  Bird Y: {status['y']:.2f}")
    print(f"  Bird VY: {status['vy']:.2f}")
    print(f"  Score: {status['score']}")
    print(f"  Pipes: {len(status['pipes'])}")

if __name__ == "__main__":
    main()