import java.util.*;

/**
 * Deterministic orchestration: ownership, enqueue, tick, collisions, reset, copies, winner.
 */
public class GameEngine {
    private Arena arena;
    private final Arena initialArena;
    private Map<String, Tank> tanks;
    private final Map<String, Tank> initialTanks;
    private final ScoreBoard scoreBoard;
    private final Map<String, Queue<Command>> commandQueues;
    private final List<Projectile> projectiles;

    /**
     * Creates a new game engine with the given arena and tanks.
     *
     * @param arena the arena for the game
     * @param tanks the initial tanks in the game
     * @throws IllegalArgumentException if there are fewer than 2 alive tanks,
     *                                  or if any tank has a duplicate id,
     *                                  or if any tank is not in bounds or on an obstacle
     */
    public GameEngine(Arena arena, List<Tank> tanks) {
        // Validate arena
        if (arena == null) {
            throw new IllegalArgumentException("Arena cannot be null");
        }

        // Validate tanks
        if (tanks == null) {
            throw new IllegalArgumentException("Tanks cannot be null");
        }

        if (tanks.isEmpty()) {
            throw new IllegalArgumentException("At least one tank must be provided");
        }

        // Count alive tanks and collect their IDs
        int aliveCount = 0;
        Set<String> tankIds = new HashSet<>();
        for (Tank tank : tanks) {
            if (tank == null) {
                throw new IllegalArgumentException("Tank cannot be null");
            }
            if (tankIds.contains(tank.getId())) {
                throw new IllegalArgumentException("Duplicate tank ID found: " + tank.getId());
            }
            tankIds.add(tank.getId());
            if (tank.isAlive()) {
                aliveCount++;
            }
        }

        if (aliveCount < 2) {
            throw new IllegalArgumentException("At least two tanks must be alive to start the game");
        }

        // Check that all tanks are in bounds and not on obstacles
        for (Tank tank : tanks) {
            Position pos = tank.getPosition();
            if (!arena.inBounds(pos)) {
                throw new IllegalArgumentException("Tank " + tank.getId() + " is out of bounds at position " + pos);
            }
            if (arena.isObstacle(pos)) {
                throw new IllegalArgumentException("Tank " + tank.getId() + " is placed on an obstacle at position " + pos);
            }
        }

        // Store initial state
        this.initialArena = arena.copy();
        this.arena = arena.copy();

        // Initialize tanks map and initial tanks map
        this.tanks = new HashMap<>();
        this.initialTanks = new HashMap<>();
        this.commandQueues = new HashMap<>();
        this.projectiles = new ArrayList<>();

        for (Tank tank : tanks) {
            // Create two independent copies as required
            Tank initialCopy = tank.copy();
            Tank currentCopy = tank.copy();
            
            this.initialTanks.put(tank.getId(), initialCopy);
            this.tanks.put(tank.getId(), currentCopy);
            
            // Initialize command queue
            this.commandQueues.put(tank.getId(), new LinkedList<>());
        }

        // Initialize score board
        this.scoreBoard = new ScoreBoard(tankIds);
    }

    /**
     * Enqueues a command for the specified tank.
     *
     * @param tankId the ID of the tank to enqueue the command for
     * @param cmd the command to enqueue
     * @throws IllegalArgumentException if the tank ID does not exist
     */
    public void enqueue(String tankId, Command cmd) {
        if (!commandQueues.containsKey(tankId)) {
            throw new IllegalArgumentException("No tank found with ID: " + tankId);
        }
        commandQueues.get(tankId).add(cmd);
    }

    /**
     * Processes one tick of the game.
     * Each live tank in lexicographic order processes at most one command.
     * Then all projectiles are advanced and checked for collisions.
     */
    public void tick() {
        // Get tank IDs sorted lexicographically
        List<String> sortedTankIds = new ArrayList<>(tanks.keySet());
        Collections.sort(sortedTankIds);

        // Process commands for each live tank
        for (String tankId : sortedTankIds) {
            Tank tank = tanks.get(tankId);
            if (!tank.isAlive()) {
                continue;
            }

            Queue<Command> queue = commandQueues.get(tankId);
            if (queue.isEmpty()) {
                continue;
            }

            Command cmd = queue.poll();

            switch (cmd) {
                case MOVE_FORWARD:
                    moveForward(tank);
                    break;
                case TURN_LEFT:
                    tank.rotateLeft();
                    break;
                case TURN_RIGHT:
                    tank.rotateRight();
                    break;
                case FIRE:
                    fire(tank);
                    break;
            }
        }

        // Advance projectiles and check for collisions
        advanceProjectiles();
    }

    /**
     * Moves the given tank one cell forward if possible.
     * The tank stops if it would go out of bounds, hit an obstacle,
     * or collide with another live tank.
     *
     * @param tank the tank to move
     */
    private void moveForward(Tank tank) {
        Position newPosition = tank.getPosition().translate(tank.getOrientation().dx(), tank.getOrientation().dy());

        // Check bounds
        if (!arena.inBounds(newPosition)) {
            return;
        }

        // Check obstacle
        if (arena.isObstacle(newPosition)) {
            return;
        }

        // Check for collision with another live tank
        for (Tank otherTank : tanks.values()) {
            if (otherTank.isAlive() && otherTank != tank && otherTank.getPosition().equals(newPosition)) {
                return;
            }
        }

        // Move the tank
        tank.setPosition(newPosition);
    }

    /**
     * Fires a projectile from the given tank.
     * The projectile is placed in front of the tank in its current orientation.
     * It is not fired if the cell in front is out of bounds or an obstacle.
     *
     * @param tank the tank that fires the projectile
     */
    private void fire(Tank tank) {
        Position firePosition = tank.getPosition().translate(tank.getOrientation().dx(), tank.getOrientation().dy());

        // Check bounds
        if (!arena.inBounds(firePosition)) {
            return;
        }

        // Check obstacle
        if (arena.isObstacle(firePosition)) {
            return;
        }

        // Create projectile
        Projectile projectile = new Projectile(tank.getId(), firePosition, tank.getOrientation());
        projectiles.add(projectile);
    }

    /**
     * Advances all projectiles one cell and handles collisions.
     */
    private void advanceProjectiles() {
        Iterator<Projectile> iterator = projectiles.iterator();
        while (iterator.hasNext()) {
            Projectile projectile = iterator.next();
            Position oldPosition = projectile.getPosition();
            Position newPosition = oldPosition.translate(projectile.getOrientation().dx(), projectile.getOrientation().dy());

            // Check if projectile is out of bounds
            if (!arena.inBounds(newPosition)) {
                iterator.remove();
                continue;
            }

            // Check if projectile hits an obstacle
            if (arena.isObstacle(newPosition)) {
                iterator.remove();
                continue;
            }

            // Check for collision with tanks
            boolean hit = false;
            for (Tank tank : tanks.values()) {
                if (!tank.isAlive() || tank.getId().equals(projectile.getShooterId())) {
                    continue;
                }

                if (tank.getPosition().equals(newPosition)) {
                    // Apply damage
                    tank.applyDamage(1);
                    
                    // Add hit to score board
                    scoreBoard.addHit(projectile.getShooterId());
                    
                    // Add kill if tank dies
                    if (!tank.isAlive()) {
                        scoreBoard.addKill(projectile.getShooterId());
                    }
                    
                    // Remove projectile on hit
                    iterator.remove();
                    hit = true;
                    break;
                }
            }

            // If no hit, move projectile
            if (!hit) {
                projectile.setPosition(newPosition);
            }
        }
    }

    /**
     * Resets the game to its initial state.
     * This includes resetting the arena, tanks, projectiles, and command queues.
     */
    public void reset() {
        this.arena = initialArena.copy();
        this.tanks = new HashMap<>();
        for (Tank initialTank : initialTanks.values()) {
            this.tanks.put(initialTank.getId(), initialTank.copy());
        }
        
        // Clear command queues
        for (Queue<Command> queue : commandQueues.values()) {
            queue.clear();
        }
        
        // Clear projectiles
        projectiles.clear();
        
        // Reset score board
        scoreBoard.reset(initialTanks.keySet());
    }

    /**
     * Returns a defensive copy of the current tanks.
     *
     * @return a map of tank IDs to tank copies
     */
    public Map<String, Tank> getTanksCopy() {
        Map<String, Tank> result = new HashMap<>();
        for (Map.Entry<String, Tank> entry : tanks.entrySet()) {
            result.put(entry.getKey(), entry.getValue().copy());
        }
        return result;
    }

    /**
     * Returns a defensive copy of the current projectiles.
     *
     * @return a list of projectile copies
     */
    public List<Projectile> getProjectilesCopy() {
        List<Projectile> result = new ArrayList<>();
        for (Projectile projectile : projectiles) {
            result.add(projectile.copy());
        }
        return result;
    }

    /**
     * Returns a defensive copy of the score board.
     *
     * @return a copy of the score board
     */
    public ScoreBoard getScoreBoardCopy() {
        return scoreBoard.copy();
    }

    /**
     * Returns the current arena.
     *
     * @return the arena
     */
    public Arena getArena() {
        return arena;
    }

    /**
     * Determines the winner of the game.
     * Returns the ID of the sole surviving tank if exactly one tank is alive
     * and there were at least two initial tanks.
     * Otherwise, returns null.
     *
     * @return the winner's ID or null if no winner
     */
    public String winner() {
        List<String> aliveTanks = new ArrayList<>();
        for (Tank tank : tanks.values()) {
            if (tank.isAlive()) {
                aliveTanks.add(tank.getId());
            }
        }

        // Must be exactly one alive tank and at least two initial tanks
        if (aliveTanks.size() == 1 && initialTanks.size() >= 2) {
            return aliveTanks.get(0);
        }

        return null;
    }
}