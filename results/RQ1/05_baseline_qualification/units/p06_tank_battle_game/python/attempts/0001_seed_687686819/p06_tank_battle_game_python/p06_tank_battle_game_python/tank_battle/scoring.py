"""ScoreBoard tracking hits and kills."""

from typing import List, Dict


class ScoreBoard:
    """Tracks hits and kills for players and calculates scores."""

    def __init__(self, player_ids: List[str]) -> None:
        """
        Initialize the scoreboard with player IDs.

        Args:
            player_ids: A list of player IDs to track.
        """
        self.hits: Dict[str, int] = {player_id: 0 for player_id in player_ids}
        self.kills: Dict[str, int] = {player_id: 0 for player_id in player_ids}

    def record_hit(self, player_id: str) -> None:
        """
        Record a hit for a player.

        Args:
            player_id: The ID of the player who made the hit.
        """
        if player_id in self.hits:
            self.hits[player_id] += 1

    def record_kill(self, player_id: str) -> None:
        """
        Record a kill for a player.

        Args:
            player_id: The ID of the player who made the kill.
        """
        if player_id in self.kills:
            self.kills[player_id] += 1

    def score(self, player_id: str) -> int:
        """
        Calculate the score for a player.

        Args:
            player_id: The ID of the player.

        Returns:
            The calculated score (hits + 5 * kills).
        """
        return self.hits[player_id] + 5 * self.kills[player_id]