"""Entry point for the brick breaker game demo.

This module provides the Main class with a run_demo method that
constructs a game, runs one deterministic tick, and returns a snapshot.
"""

from brick_breaker import Game


class Main:
    """Main entry point for the brick breaker game."""

    @staticmethod
    def run_demo() -> dict:
        """Run a single deterministic demo step of the game.

        Constructs a Game with default configuration, executes one tick
        with no input, and returns the resulting game state snapshot.

        Returns:
            A dictionary containing the game state after one tick.
        """
        # Create game with default configuration
        game = Game()
        
        # Run one deterministic tick with no input
        snapshot = game.tick("none")
        
        return snapshot