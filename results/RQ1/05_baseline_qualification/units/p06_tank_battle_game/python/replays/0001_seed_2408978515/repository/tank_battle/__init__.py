"""Public API re-exports for the tank battle game."""

from .game import Game
from .arena import Arena
from .obstacle import Obstacle
from .geometry import Rect
from .tank import Tank
from .projectile import Projectile
from .scoring import ScoreBoard
from .directions import Direction
from .commands import Command, MoveForward, RotateLeft, RotateRight, RotateTo, Fire
from .configs import build_default_demo

__all__ = [
    "Game",
    "Arena",
    "Obstacle",
    "Rect",
    "Tank",
    "Projectile",
    "ScoreBoard",
    "Direction",
    "Command",
    "MoveForward",
    "RotateLeft",
    "RotateRight",
    "RotateTo",
    "Fire",
    "build_default_demo",
]