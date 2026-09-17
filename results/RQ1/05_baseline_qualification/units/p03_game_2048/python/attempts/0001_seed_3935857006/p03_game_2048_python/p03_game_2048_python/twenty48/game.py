"""Game orchestration module for the 2048 game."""

import random
from typing import Tuple
from .board import Board
from .types import Direction, GameStatus


class Game:
    """Orchestrates the 2048 game logic with deterministic RNG and game lifecycle."""

    def __init__(self, seed: int = 0) -> None:
        """
        Initialize the game with a deterministic random number generator.
        
        Args:
            seed: Seed for the random number generator to ensure deterministic behavior
        """
        self._rng = random.Random(seed)
        self._board = Board()
        self._score = 0
        self._status = GameStatus.RUNNING

    def reset(self) -> None:
        """Reset the game to initial state with two random tiles spawned."""
        self._board.reset_empty()
        self._score = 0
        self._status = GameStatus.RUNNING
        
        # Spawn two random tiles
        self._board.add_random_tile(self._rng)
        self._board.add_random_tile(self._rng)

    def move(self, direction: Direction) -> bool:
        """
        Execute a move in the specified direction.
        
        Args:
            direction: The direction to move tiles
            
        Returns:
            True if the board state changed as a result of the move, False otherwise
        """
        if self._status != GameStatus.RUNNING:
            return False
            
        changed, gained_score = self._board.move(direction)
        
        if changed:
            self._score += gained_score
            
            # Check for win condition
            if self._board.has_target():
                self._status = GameStatus.WON
            else:
                # Add a new random tile
                self._board.add_random_tile(self._rng)
                
                # Check for loss condition
                if not self._board.can_move():
                    self._status = GameStatus.LOST
                    
        return changed

    def get_status(self) -> GameStatus:
        """
        Get the current game status.
        
        Returns:
            Current game status
        """
        return self._status

    def get_score(self) -> int:
        """
        Get the current game score.
        
        Returns:
            Current game score
        """
        return self._score

    def get_board(self) -> Board:
        """
        Get the game board.
        
        Returns:
            The game board instance
        """
        return self._board