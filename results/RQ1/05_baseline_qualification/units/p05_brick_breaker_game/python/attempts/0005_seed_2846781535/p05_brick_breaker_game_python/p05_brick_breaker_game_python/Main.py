"""Entry point for the brick breaker game demonstrating a single deterministic tick."""

from brick_breaker import Game


class Main:
    """Main class for running the brick breaker demo."""

    @staticmethod
    def run_demo() -> dict:
        """Run a single deterministic tick of the game and return the state snapshot.
        
        Returns:
            Dictionary containing the game state after one tick
        """
        # Create a new game instance with default configuration
        game = Game()
        
        # Execute exactly one tick with no input action
        return game.tick('none')


if __name__ == "__main__":
    # Run the demo when this script is executed directly
    result = Main.run_demo()
    print(result)