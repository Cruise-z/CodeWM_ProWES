"""Default demo configuration for the tank battle game."""

from .arena import Arena
from .obstacle import Obstacle
from .geometry import Rect
from .tank import Tank
from .directions import Direction
from .game import Game


def build_default_demo() -> Game:
    """
    Build the default demo game with a fixed arena and two tanks.

    Returns:
        A Game instance with Arena(8, 5, []) and two tanks:
        Tank("p1", "P1", 1, 2, Direction.E, 3, 1) and
        Tank("p2", "P2", 6, 2, Direction.W, 3, 1)
    """
    # Create the arena
    arena = Arena(8, 5, [])
    
    # Create the two tanks
    tank1 = Tank("p1", "P1", 1, 2, Direction.E, 3, 1)
    tank2 = Tank("p2", "P2", 6, 2, Direction.W, 3, 1)
    
    # Create the tanks dictionary
    tanks = {"p1": tank1, "p2": tank2}
    
    # Create and return the game
    return Game(arena, tanks)