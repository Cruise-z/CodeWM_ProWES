"""Main entry point for the brick breaker game demo."""

from .brick_breaker import Game


class Main:
    """Main class for running the brick breaker game demo."""

    @staticmethod
    def run_demo() -> dict:
        """
        Run a single deterministic demo step of the game.
        
        Returns:
            A snapshot dictionary of the game state after one tick
        """
        # Create a game instance with default configuration
        game = Game()
        
        # Perform one tick with no input
        return game.tick("none")


if __name__ == "__main__":
    # Run the demo and print the result
    result = Main.run_demo()
    print(result)