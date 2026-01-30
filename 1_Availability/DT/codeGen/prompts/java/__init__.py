# expose leaf modules as attributes: prompts.java.snakegame
from . import snakeGame  # noqa: F401
from . import game2048  # noqa: F401
from . import calculator  # noqa: F401
from . import flappyBird  # noqa: F401
from . import caroGame  # noqa: F401
from . import brickBreaker  # noqa: F401
from . import customerMS  # noqa: F401
from . import tankBattle # noqa: F401
from . import qrCodeGenDet  # noqa: F401
from . import toDoListApp  # noqa: F401
from . import videoPlayer  # noqa: F401

__all__ = ["snakeGame", "game2048", "calculator", "flappyBird", "caroGame", "brickBreaker", "customerMS", "tankBattle", "qrCodeGenDet", "toDoListApp", "videoPlayer"]
