"""Entry point for the brick breaker game demo.

This module provides a thin entry point that demonstrates the game
functionality with a single deterministic tick.
"""

from brick_breaker import Game


class Main:
    """Main entry point for the brick breaker game demo."""

    @staticmethod
    def run_demo() -> dict:
        """Run a single deterministic demo tick of the game.

        Returns:
            A snapshot dictionary representing the game state after one tick.
        """
        # Create a new game with default configuration
        game = Game()
        
        # Perform one tick with no input action
        snapshot = game.tick('none')
        
        return snapshot


if __name__ == "__main__":
    # Run the demo and print the result
    result = Main.run_demo()
    print(result)