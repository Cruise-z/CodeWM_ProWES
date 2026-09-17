"""Entry point for the Brick Breaker game demo."""

from .brick_breaker import Game, GameConfig


class Main:
    """Main class for running the Brick Breaker demo."""

    @staticmethod
    def run_demo() -> dict:
        """Run a single deterministic demo step and return the game state.

        Returns:
            A dictionary containing the game state snapshot after one tick.
        """
        # Create a new game with default configuration
        game = Game(GameConfig())
        
        # Perform one deterministic tick with no input
        return game.tick("none")


if __name__ == "__main__":
    # Run the demo when this script is executed directly
    result = Main.run_demo()
    print(result)