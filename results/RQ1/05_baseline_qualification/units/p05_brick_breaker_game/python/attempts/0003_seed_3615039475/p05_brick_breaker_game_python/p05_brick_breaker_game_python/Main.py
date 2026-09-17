"""Entry point for the brick breaker game demo.

This module provides the Main class with a run_demo method that
executes a single deterministic game tick and returns the resulting state.
"""

from .brick_breaker import Game, GameConfig


class Main:
    """Main entry point for the brick breaker game.

    Provides a static method to run a single deterministic demo step.
    """

    @staticmethod
    def run_demo() -> dict:
        """Run a single deterministic demo tick of the game.

        Constructs a Game with default configuration, executes one tick
        with no input, and returns the resulting game state snapshot.

        Returns:
            A dictionary containing the game state after one tick:
            {
                'score': int,
                'lives': int,
                'status': str,
                'bricks_remaining': int,
                'ball': {'x': float, 'y': float, 'vx': float, 'vy': float},
                'paddle': {'x': float, 'y': float}
            }
        """
        # Construct game with default configuration
        game = Game(GameConfig())
        
        # Execute one deterministic tick with no input
        return game.tick('none')