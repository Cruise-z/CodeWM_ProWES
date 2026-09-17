"""Game orchestration: validation, tick, reset, snapshot, winner."""

from .commands import Command, MoveForward, RotateLeft, RotateRight, RotateTo, Fire
from .arena import Arena
from .tank import Tank
from .projectile import Projectile
from .scoring import ScoreBoard
from typing import Dict, List, Tuple, Optional, Union


class Game:
    """Orchestrates the tank battle game state and rules.

    Attributes:
        arena: The game arena with boundaries and obstacles.
        tanks: Dictionary mapping tank IDs to Tank instances.
        projectiles: List of active projectiles in the game.
        scores: ScoreBoard tracking hits and kills.
        command_queue: List of queued commands to be processed.
        next_projectile_id: Next available ID for new projectiles.
        _initial_arena: Immutable deep copy of initial arena state.
        _initial_tanks: Immutable deep copy of initial tank states.
    """

    def __init__(self, arena: Arena, tanks: Dict[str, Tank]):
        """Initialize a game with given arena and tanks.

        Validates that all tank positions are unique, in-bounds, and unblocked.

        Args:
            arena: The game arena.
            tanks: Dictionary mapping tank IDs to Tank instances.

        Raises:
            ValueError: If tank positions conflict or are invalid.
        """
        # Validate unique positions
        positions = set()
        for tank in tanks.values():
            pos = (tank.x, tank.y)
            if pos in positions:
                raise ValueError(f"Duplicate tank position at {pos}")
            positions.add(pos)

        # Validate positions are in bounds and unblocked
        for tank in tanks.values():
            if not arena.in_bounds(tank.x, tank.y):
                raise ValueError(f"Tank {tank.id} position ({tank.x}, {tank.y}) "
                                f"is out of bounds for arena {arena.width}x{arena.height}")
            if arena.is_blocked(tank.x, tank.y):
                raise ValueError(f"Tank {tank.id} position ({tank.x}, {tank.y}) "
                                "is blocked by an obstacle")

        # Store initial state for reset
        self._initial_arena = arena
        self._initial_tanks = {tid: tank.clone() for tid, tank in tanks.items()}

        # Initialize mutable state
        self.arena = arena
        self.tanks = tanks
        self.projectiles: List[Projectile] = []
        self.scores = ScoreBoard(list(tanks.keys()))
        self.command_queue: List[Tuple[str, Command]] = []
        self.next_projectile_id = 0

    def queue_command(self, player_id: str, command: Command) -> None:
        """Queue a command for a player.

        Args:
            player_id: The ID of the player issuing the command.
            command: The command to queue.
        """
        self.command_queue.append((player_id, command))

    def tick(self) -> None:
        """Process one game tick.

        Executes queued commands in order (stable-sorted by player ID),
        then processes all projectiles in order of PID.
        """
        # Sort commands by player ID for stable ordering
        self.command_queue.sort(key=lambda x: x[0])

        # Apply commands
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

        # Clear the command queue after applying
        self.command_queue.clear()

        # Process projectiles
        # Sort projectiles by PID for consistent order
        self.projectiles.sort(key=lambda p: p.pid)
        i = 0
        while i < len(self.projectiles):
            proj = self.projectiles[i]
            # Move projectile
            proj.move()

            # Check if projectile is out of bounds or blocked
            if self.arena.is_blocked(proj.x, proj.y):
                self.projectiles.pop(i)
                continue

            # Check for collision with a tank
            hit_tank = None
            for tank in self.tanks.values():
                if tank.alive() and tank.id != proj.owner_id:
                    if tank.x == proj.x and tank.y == proj.y:
                        hit_tank = tank
                        break

            if hit_tank is not None:
                # Deal damage
                hit_tank.health -= 1
                self.scores.record_hit(proj.owner_id)

                # Check if tank is destroyed
                if not hit_tank.alive():
                    self.scores.record_kill(proj.owner_id)

                # Remove projectile
                self.projectiles.pop(i)
                continue

            # Projectile survived this step
            i += 1

    def _apply_move_forward(self, player_id: str, steps: int) -> None:
        """Apply a move forward command to a tank.

        Moves the tank one cell at a time, stopping before bounds,
        obstacle, or another tank.

        Args:
            player_id: The ID of the player commanding the move.
            steps: Number of steps to move forward.
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

            # Stop if another tank is present
            if any(tank.x == new_x and tank.y == new_y and t.alive()
                   for t in self.tanks.values() if t.id != player_id):
                break

            # Move the tank
            tank.x = new_x
            tank.y = new_y

    def _apply_rotate_left(self, player_id: str) -> None:
        """Apply a rotate left command to a tank.

        Args:
            player_id: The ID of the player commanding the rotation.
        """
        tank = self.tanks[player_id]
        tank.direction = tank.direction.left()

    def _apply_rotate_right(self, player_id: str) -> None:
        """Apply a rotate right command to a tank.

        Args:
            player_id: The ID of the player commanding the rotation.
        """
        tank = self.tanks[player_id]
        tank.direction = tank.direction.right()

    def _apply_rotate_to(self, player_id: str, direction: "Direction") -> None:
        """Apply a rotate to command to a tank.

        Args:
            player_id: The ID of the player commanding the rotation.
            direction: The direction to face.
        """
        tank = self.tanks[player_id]
        tank.direction = direction

    def _apply_fire(self, player_id: str) -> None:
        """Apply a fire command from a tank.

        Creates a new projectile at the tank's barrel if the cell is free.

        Args:
            player_id: The ID of the player firing.
        """
        tank = self.tanks[player_id]
        barrel_x, barrel_y = tank.barrel_ahead()

        # Check if the barrel cell is free
        if self.arena.is_blocked(barrel_x, barrel_y):
            return

        # Check if any live tank occupies that cell
        if any(tank.x == barrel_x and tank.y == barrel_y and tank.alive()
               for tank in self.tanks.values()):
            return

        # Create the projectile
        projectile = Projectile(
            pid=self.next_projectile_id,
            owner_id=player_id,
            x=barrel_x,
            y=barrel_y,
            direction=tank.direction
        )
        self.projectiles.append(projectile)
        self.next_projectile_id += 1

    def reset(self) -> None:
        """Reset the game to its initial state.

        Restores deep clones of the initial arena and tanks,
        clears projectiles and command queue,
        resets scores to zero hits/kills,
        and resets next_projectile_id.
        """
        self.arena = self._initial_arena
        self.tanks = {tid: tank.clone() for tid, tank in self._initial_tanks.items()}
        self.projectiles.clear()
        self.command_queue.clear()
        self.scores = ScoreBoard(list(self._initial_tanks.keys()))
        self.next_projectile_id = 0

    def winner(self) -> Optional[str]:
        """Determine the winning tank, if any.

        Returns:
            The ID of the surviving tank if exactly one remains alive
            and at least two tanks were initially present;
            otherwise None.
        """
        alive_tanks = [tid for tid, tank in self.tanks.items() if tank.alive()]
        if len(alive_tanks) == 1 and len(self._initial_tanks) >= 2:
            return alive_tanks[0]
        return None

    def snapshot(self) -> Dict[str, Union[Dict, List, Optional[str]]]:
        """Create a snapshot of the current game state.

        Returns:
            A dictionary containing:
            - arena: dict with width, height, obstacles (as list of dicts)
            - tanks: dict of tank dicts with direction serialized via .name
            - projectiles: list of projectile dicts with direction serialized via .name
            - scores: dict with hits, kills, and score mappings
            - winner: str or None
        """
        # Serialize arena
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

        # Serialize tanks
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

        # Serialize projectiles
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

        # Serialize scores
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