"""Entry point for the brick breaker game demonstration.

This module provides a static method `run_demo` that creates a game instance,
performs one deterministic tick, and returns a snapshot of the game state.
"""

from brick_breaker import Game


class Main:
    """Main entry point for the brick breaker game demonstration."""

    @staticmethod
    def run_demo() -> dict:
        """Run a single deterministic demo step of the game.

        Constructs a game with default configuration, performs one tick with
        no input, and returns a snapshot of the game state.

        Returns:
            A dictionary containing the game state snapshot.
        """
        # Create game with default configuration
        game = Game()
        
        # Perform one deterministic tick with no input
        snapshot = game.tick('none')
        
        return snapshot