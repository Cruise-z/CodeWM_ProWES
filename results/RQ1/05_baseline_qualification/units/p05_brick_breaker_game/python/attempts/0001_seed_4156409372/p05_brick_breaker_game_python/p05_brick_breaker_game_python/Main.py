"""Main entry point for the brick breaker game demo.

This module provides a thin entry point that demonstrates the game
functionality with a single deterministic tick.
"""

from .brick_breaker import Game


class Main:
    """Main class for running the game demo."""

    @staticmethod
    def run_demo() -> dict:
        """Run a single deterministic game tick and return the state snapshot.

        Returns:
            A dictionary containing the game state after one tick.
        """
        # Create a new game with default configuration
        game = Game()
        
        # Perform one tick with no input
        return game.tick("none")