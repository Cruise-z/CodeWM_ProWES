"""Runtime bootstrap for the tank battle game demo."""

from tank_battle import build_default_demo, RotateRight


def run_demo() -> dict:
    """Run a simple tank battle demo and return the snapshot.

    This function:
    1. Builds the default demo game
    2. Queues a RotateRight command for player "p1"
    3. Executes one game tick
    4. Returns the game state snapshot

    Returns:
        A dictionary containing the game state snapshot
    """
    game = build_default_demo()
    game.queue_command("p1", RotateRight())
    game.tick()
    return game.snapshot()


if __name__ == "__main__":
    result = run_demo()
    print(result)