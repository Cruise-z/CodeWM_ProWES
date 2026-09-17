"""Entry point for the brick breaker game demo.

This module provides a static method to run a single deterministic demo
step of the game and return the resulting state snapshot.
"""

from brick_breaker import Game


class Main:
    """Main entry point for the brick breaker game."""

    @staticmethod
    def run_demo() -> dict:
        """Run a single deterministic demo step of the game.

        Returns:
            A dictionary containing the game state snapshot after one tick.
        """
        # Create a new game with default configuration
        game = Game()
        
        # Execute exactly one game tick with no input
        return game.tick('none')