"""Default demo configuration for the tank battle game."""

from .arena import Arena
from .obstacle import Obstacle
from .geometry import Rect
from .tank import Tank
from .directions import Direction
from .game import Game


def build_default_demo() -> Game:
    """Build the default demo game with exact fixtures.

    Constructs:
    - An 8x5 empty arena
    - Tank "p1" at (1,2) facing East with health 3 and speed 1
    - Tank "p2" at (6,2) facing West with health 3 and speed 1

    Returns:
        A Game instance with the specified setup.
    """
    arena = Arena(8, 5, [])
    tank_p1 = Tank("p1", "P1", 1, 2, Direction.E, 3, 1)
    tank_p2 = Tank("p2", "P2", 6, 2, Direction.W, 3, 1)
    tanks = {"p1": tank_p1, "p2": tank_p2}
    return Game(arena, tanks)