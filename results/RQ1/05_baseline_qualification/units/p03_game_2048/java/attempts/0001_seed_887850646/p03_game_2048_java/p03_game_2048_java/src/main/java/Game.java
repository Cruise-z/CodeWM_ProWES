/**
 * Orchestrates the 2048 game logic, managing the board, spawner, score, and game status.
 * This class coordinates the game flow, handling resets, moves, scoring, and status updates.
 */
public final class Game {
    private final Board board;
    private final Spawner spawner;
    private int score;
    private GameStatus status;

    /**
     * Constructs a new Game with the specified board and spawner.
     *
     * @param board the game board instance
     * @param spawner the spawner for determining tile placements
     * @throws IllegalArgumentException if board or spawner is null
     */
    public Game(Board board, Spawner spawner) {
        if (board == null) {
            throw new IllegalArgumentException("Board cannot be null");
        }
        if (spawner == null) {
            throw new IllegalArgumentException("Spawner cannot be null");
        }
        this.board = board;
        this.spawner = spawner;
        this.score = 0;
        this.status = GameStatus.IN_PROGRESS;
    }

    /**
     * Resets the game to its initial state.
     * Clears the board and places exactly two tiles using the spawner.
     * Resets the score to 0 and status to IN_PROGRESS.
     */
    public void reset() {
        board.clear();
        score = 0;
        status = GameStatus.IN_PROGRESS;
        
        // Apply exactly two spawns
        Spawn spawn1 = spawner.nextSpawn();
        board.setCell(spawn1.row(), spawn1.col(), spawn1.value());
        
        Spawn spawn2 = spawner.nextSpawn();
        board.setCell(spawn2.row(), spawn2.col(), spawn2.value());
    }

    /**
     * Attempts to move the tiles in the specified direction.
     * Updates the score and applies a new tile if the move changed the board state.
     * Updates the game status after the move.
     *
     * @param dir the direction to move the tiles
     * @return the result of the move operation
     */
    public MoveResult move(Direction dir) {
        MoveResult result = board.move(dir);
        score += result.scoreGained();
        
        if (result.changed()) {
            Spawn spawn = spawner.nextSpawn();
            board.setCell(spawn.row(), spawn.col(), spawn.value());
        }
        
        // Update game status after every move attempt
        if (board.hasTileAtLeast(2048)) {
            status = GameStatus.WON;
        } else if (!board.hasAnyMoves()) {
            status = GameStatus.LOST;
        } else {
            status = GameStatus.IN_PROGRESS;
        }
        
        return result;
    }

    /**
     * Returns the current score of the game.
     *
     * @return the current score
     */
    public int getScore() {
        return score;
    }

    /**
     * Returns the current status of the game.
     *
     * @return the current game status
     */
    public GameStatus getStatus() {
        return status;
    }

    /**
     * Returns a deep copy of the current board grid.
     * The caller can modify the returned array without affecting the game board.
     *
     * @return a new 4x4 array representing the board's current state
     */
    public int[][] getGridCopy() {
        return board.getGridCopy();
    }
}