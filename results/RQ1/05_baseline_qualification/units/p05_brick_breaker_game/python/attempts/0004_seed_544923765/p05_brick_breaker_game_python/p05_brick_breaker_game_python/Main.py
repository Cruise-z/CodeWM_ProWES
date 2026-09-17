"""
Main entry point for the brick breaker game.

This module provides the Main class with a run_demo method that
performs a single deterministic game tick and returns the result.
"""

from .brick_breaker import Game, GameConfig


class Main:
    """Main class for running the brick breaker game demo."""

    @staticmethod
    def run_demo() -> dict:
        """
        Run a single deterministic demo tick of the game.

        Returns:
            A dictionary containing the game state snapshot after one tick.
        """
        # Create game with default configuration
        game = Game(GameConfig())
        
        # Perform one tick with no input
        return game.tick("none")


if __name__ == "__main__":
    # Run the demo when this script is executed directly
    result = Main.run_demo()
    print(result)