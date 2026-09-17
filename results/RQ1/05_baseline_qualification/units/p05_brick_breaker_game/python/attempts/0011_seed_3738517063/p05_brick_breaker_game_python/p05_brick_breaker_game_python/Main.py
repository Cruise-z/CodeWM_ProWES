"""Main entry point for the brick breaker game demo.

This module provides a thin entry point that demonstrates the game
functionality with a single deterministic tick.
"""

from brick_breaker import Game


class Main:
    """Main class for runtime bootstrap and demo execution."""

    @staticmethod
    def run_demo() -> dict:
        """Run a single deterministic demo step of the game.

        Returns:
            A snapshot dictionary containing the game state after one tick.
        """
        # Construct game with default configuration
        game = Game()
        
        # Perform one deterministic tick with no input
        snapshot = game.tick('none')
        
        return snapshot


if __name__ == "__main__":
    # Run the demo when executed directly
    result = Main.run_demo()
    print(result)