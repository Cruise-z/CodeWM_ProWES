# expose leaf modules as attributes: prompts.java.snakegame
from . import brickBreaker  # noqa: F401
from . import tankBattle  # noqa: F401 

__all__ = ["brickBreaker", "tankBattle"]