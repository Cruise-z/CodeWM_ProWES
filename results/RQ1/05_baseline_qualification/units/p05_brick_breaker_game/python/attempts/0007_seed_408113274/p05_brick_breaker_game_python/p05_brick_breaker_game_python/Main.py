"""Main entry point for the brick breaker game demonstration.

This module provides a thin entry point that runs a single deterministic
demo step and exits. It's designed to be used for protocol testing and
demonstration purposes.
"""

from brick_breaker import Game


class Main:
    """Main class for running the brick breaker game demo."""

    @staticmethod
    def run_demo() -> dict:
        """Run a single deterministic demo step of the game.

        Constructs a game with default configuration, performs one tick
        with no input, and returns the resulting game state snapshot.

        Returns:
            A dictionary containing the game state snapshot after one tick.
        """
        # Create game instance with default configuration
        game = Game()
        
        # Perform one deterministic tick with no input
        return game.tick('none')


if __name__ == "__main__":
    # Run the demo when this script is executed directly
    result = Main.run_demo()
    print(result)