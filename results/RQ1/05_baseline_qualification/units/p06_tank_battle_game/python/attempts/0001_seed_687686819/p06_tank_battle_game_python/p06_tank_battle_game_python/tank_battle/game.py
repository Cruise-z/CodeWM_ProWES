"""Game orchestration: validation, tick, reset, snapshot, winner."""

from typing import Dict, List, Optional, Tuple
from .commands import Command, MoveForward, RotateLeft, RotateRight, RotateTo, Fire
from .arena import Arena
from .tank import Tank
from .projectile import Projectile
from .scoring import ScoreBoard


class Game:
    """Main game class that orchestrates the tank battle."""

    def __init__(self, arena: Arena, tanks: Dict[str, Tank]) -> None:
        """
        Initialize the game with an arena and tanks.

        Args:
            arena: The arena where the game takes place.
            tanks: A dictionary mapping tank IDs to Tank objects.

        Raises:
            ValueError: If tanks are not unique, in-bounds, or unblocked.
        """
        # Validate initial tank positions
        tank_positions = set()
        for tank in tanks.values():
            if tank.id in tank_positions:
                raise ValueError(f"Duplicate tank ID: {tank.id}")
            if not arena.in_bounds(tank.x, tank.y):
                raise ValueError(
                    f"Tank {tank.id} position ({tank.x}, {tank.y}) "
                    f"is out of bounds for arena of size ({arena.width}, {arena.height})"
                )
            if arena.is_blocked(tank.x, tank.y):
                raise ValueError(
                    f"Tank {tank.id} position ({tank.x}, {tank.y}) "
                    "is blocked by an obstacle"
                )
            tank_positions.add(tank.id)

        # Store initial state for reset
        self._initial_arena = arena
        self._initial_tanks = {tid: tank.clone() for tid, tank in tanks.items()}

        # Initialize mutable state
        self.arena = arena
        self.tanks = tanks
        self.projectiles: List[Projectile] = []
        self.scores = ScoreBoard(list(tanks))
        self.command_queue: List[Tuple[str, Command]] = []
        self.next_projectile_id = 0

    def queue_command(self, player_id: str, command: Command) -> None:
        """
        Queue a command for a player.

        Args:
            player_id: The ID of the player issuing the command.
            command: The command to queue.
        """
        self.command_queue.append((player_id, command))

    def tick(self) -> None:
        """
        Execute one game tick.

        This processes all queued commands in order, then moves all projectiles
        in the same tick, handling collisions and scoring.
        """
        # Sort commands by player ID for deterministic order
        self.command_queue.sort(key=lambda x: x[0])

        # Process commands
        for player_id, command in self.command_queue:
            if isinstance(command, MoveForward):
                self._apply_move_forward(player_id, command.steps)
            elif isinstance(command, RotateLeft):
                self._apply_rotate_left(player_id)
            elif isinstance(command, RotateRight):
                self._apply_rotate_right(player_id)
            elif isinstance(command, RotateTo):
                self._apply_rotate_to(player_id, command.direction)
            elif isinstance(command, Fire):
                self._apply_fire(player_id)

        # Clear the command queue after processing
        self.command_queue.clear()

        # Process projectiles in order of PID
        # We need to sort by PID to ensure consistent behavior
        self.projectiles.sort(key=lambda p: p.pid)
        
        # Move all projectiles and handle collisions
        i = 0
        while i < len(self.projectiles):
            projectile = self.projectiles[i]
            # Move projectile
            projectile.move()
            
            # Check if projectile is out of bounds or blocked
            if self.arena.is_blocked(projectile.x, projectile.y):
                self.projectiles.pop(i)
                continue
            
            # Check for collisions with tanks
            hit_tank = None
            for tank in self.tanks.values():
                if tank.alive() and tank.id != projectile.owner_id:
                    if tank.x == projectile.x and tank.y == projectile.y:
                        hit_tank = tank
                        break
            
            if hit_tank is not None:
                # Reduce health of hit tank
                hit_tank.health -= 1
                
                # Record hit
                self.scores.record_hit(projectile.owner_id)
                
                # If tank is dead, record kill
                if not hit_tank.alive():
                    self.scores.record_kill(projectile.owner_id)
                
                # Remove projectile
                self.projectiles.pop(i)
                continue
            
            # Move to next projectile
            i += 1

    def _apply_move_forward(self, player_id: str, steps: int) -> None:
        """
        Apply a move forward command.

        Args:
            player_id: The ID of the player issuing the command.
            steps: Number of steps to move.
        """
        tank = self.tanks[player_id]
        dx, dy = tank.direction.delta()
        for _ in range(steps):
            new_x = tank.x + dx
            new_y = tank.y + dy
            
            # Stop if out of bounds
            if not self.arena.in_bounds(new_x, new_y):
                break
            
            # Stop if blocked
            if self.arena.is_blocked(new_x, new_y):
                break
            
            # Stop if another tank is in the way
            if any(
                other_tank.x == new_x and other_tank.y == new_y and other_tank.alive()
                for other_tank in self.tanks.values()
                if other_tank.id != player_id
            ):
                break
            
            # Move the tank
            tank.x = new_x
            tank.y = new_y

    def _apply_rotate_left(self, player_id: str) -> None:
        """
        Apply a rotate left command.

        Args:
            player_id: The ID of the player issuing the command.
        """
        tank = self.tanks[player_id]
        tank.direction = tank.direction.left()

    def _apply_rotate_right(self, player_id: str) -> None:
        """
        Apply a rotate right command.

        Args:
            player_id: The ID of the player issuing the command.
        """
        tank = self.tanks[player_id]
        tank.direction = tank.direction.right()

    def _apply_rotate_to(self, player_id: str, direction: "Direction") -> None:
        """
        Apply a rotate to command.

        Args:
            player_id: The ID of the player issuing the command.
            direction: The direction to rotate to.
        """
        tank = self.tanks[player_id]
        tank.direction = direction

    def _apply_fire(self, player_id: str) -> None:
        """
        Apply a fire command.

        Args:
            player_id: The ID of the player issuing the command.
        """
        tank = self.tanks[player_id]
        barrel_x, barrel_y = tank.barrel_ahead()
        
        # Check if the barrel position is free
        if not self.arena.in_bounds(barrel_x, barrel_y):
            return
        if self.arena.is_blocked(barrel_x, barrel_y):
            return
        if any(
            other_tank.x == barrel_x and other_tank.y == barrel_y and other_tank.alive()
            for other_tank in self.tanks.values()
            if other_tank.id != player_id
        ):
            return
        
        # Create new projectile
        projectile = Projectile(
            pid=self.next_projectile_id,
            owner_id=player_id,
            x=barrel_x,
            y=barrel_y,
            direction=tank.direction,
            speed=tank.speed
        )
        self.projectiles.append(projectile)
        self.next_projectile_id += 1

    def reset(self) -> None:
        """
        Reset the game to its initial state.
        """
        # Restore initial arena and tanks
        self.arena = self._initial_arena
        self.tanks = {tid: tank.clone() for tid, tank in self._initial_tanks.items()}
        
        # Clear projectiles and command queue
        self.projectiles.clear()
        self.command_queue.clear()
        
        # Reset scores
        self.scores = ScoreBoard(list(self._initial_tanks))
        
        # Reset projectile ID counter
        self.next_projectile_id = 0

    def winner(self) -> Optional[str]:
        """
        Determine the winner of the game.

        Returns:
            The ID of the winning tank if exactly one tank remains alive and 
            at least two tanks were initially present, otherwise None.
        """
        alive_tanks = [tid for tid, tank in self.tanks.items() if tank.alive()]
        
        # Return the winner only if there's exactly one alive tank 
        # and at least two tanks were initially present
        if len(alive_tanks) == 1 and len(self._initial_tanks) >= 2:
            return alive_tanks[0]
        return None

    def snapshot(self) -> Dict:
        """
        Create a snapshot of the current game state.

        Returns:
            A dictionary representation of the game state with no mutable objects.
        """
        # Convert arena to dict
        arena_dict = {
            "width": self.arena.width,
            "height": self.arena.height,
            "obstacles": [
                {"rect": {
                    "x": obs.rect.x,
                    "y": obs.rect.y,
                    "w": obs.rect.w,
                    "h": obs.rect.h
                }}
                for obs in self.arena.obstacles
            ]
        }

        # Convert tanks to dict of dicts
        tanks_dict = {}
        for tid, tank in self.tanks.items():
            tanks_dict[tid] = {
                "id": tank.id,
                "name": tank.name,
                "x": tank.x,
                "y": tank.y,
                "direction": tank.direction.name,
                "health": tank.health,
                "speed": tank.speed
            }

        # Convert projectiles to list of dicts
        projectiles_list = []
        for proj in self.projectiles:
            projectiles_list.append({
                "pid": proj.pid,
                "owner_id": proj.owner_id,
                "x": proj.x,
                "y": proj.y,
                "direction": proj.direction.name,
                "speed": proj.speed
            })

        # Convert scores to dict
        scores_dict = {
            "hits": self.scores.hits.copy(),
            "kills": self.scores.kills.copy(),
            "scores": {
                tid: self.scores.score(tid) for tid in self.scores.hits.keys()
            }
        }

        # Get winner
        winner_id = self.winner()

        return {
            "arena": arena_dict,
            "tanks": tanks_dict,
            "projectiles": projectiles_list,
            "scores": scores_dict,
            "winner": winner_id
        }