"""ScoreBoard tracking hits and kills."""

from typing import List, Dict


class ScoreBoard:
    """Tracks hits and kills for players and calculates scores.

    Attributes:
        hits: Dictionary mapping player IDs to their hit counts.
        kills: Dictionary mapping player IDs to their kill counts.
    """

    def __init__(self, player_ids: List[str]):
        """Initialize a scoreboard with zero hits and kills for each player.

        Args:
            player_ids: List of player IDs to track.
        """
        self.hits: Dict[str, int] = {player_id: 0 for player_id in player_ids}
        self.kills: Dict[str, int] = {player_id: 0 for player_id in player_ids}

    def record_hit(self, player_id: str) -> None:
        """Record a hit for the specified player.

        Args:
            player_id: The ID of the player who made the hit.
        """
        self.hits[player_id] += 1

    def record_kill(self, player_id: str) -> None:
        """Record a kill for the specified player.

        Args:
            player_id: The ID of the player who made the kill.
        """
        self.kills[player_id] += 1

    def score(self, player_id: str) -> int:
        """Calculate the total score for a player.

        Score is calculated as hits + 5 * kills.

        Args:
            player_id: The ID of the player.

        Returns:
            The total score for the player.
        """
        return self.hits[player_id] + 5 * self.kills[player_id]