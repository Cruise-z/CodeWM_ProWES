/**
 * Orchestration class implementing the canonical Game API.
 * Manages game state, board, players, and game flow according to the rules.
 */
public final class Game {
    private final Board board;
    private Player currentPlayer;
    private GameState state;
    private final java.util.List<Move> history;

    /**
     * Creates a new Game with the specified board size.
     * Initializes the board, sets the first player to X, and starts in progress state.
     *
     * @param size the size of the square board (must be >= 5)
     * @throws IllegalArgumentException if size < 5
     */
    public Game(int size) {
        if (size < 5) {
            throw new IllegalArgumentException("Board size must be at least 5");
        }
        this.board = new Board(size);
        this.currentPlayer = Player.X;
        this.state = GameState.inProgress();
        this.history = new java.util.ArrayList<>();
    }

    /**
     * Returns the current board state.
     * Tests may call snapshot for inspection but should use only Game API.
     *
     * @return the board instance
     */
    public Board getBoard() {
        return board;
    }

    /**
     * Returns the player whose turn it currently is.
     *
     * @return the current player
     */
    public Player getCurrentPlayer() {
        return currentPlayer;
    }

    /**
     * Returns the current state of the game.
     *
     * @return the game state
     */
    public GameState getState() {
        return state;
    }

    /**
     * Attempts to place a move at the specified position.
     * Behavior only when state is IN_PROGRESS:
     * - If out-of-bounds or occupied, return false with no mutation
     * - Otherwise place currentPlayer stone, append Move to history
     * - Evaluate win via WinDetector.hasFiveInRow
     * - If win, set state to won(currentPlayer) and do NOT toggle currentPlayer
     * - Else if board is full, set state to draw()
     * - Else leave state as IN_PROGRESS and toggle currentPlayer
     * When state is terminal (DRAW or *_WON), any call returns false with no mutation
     *
     * @param row the row coordinate
     * @param col the column coordinate
     * @return true if move was successfully placed, false otherwise
     */
    public boolean placeMove(int row, int col) {
        // Cannot place move if game is already terminal
        if (state.getStatus() != GameState.Status.IN_PROGRESS) {
            return false;
        }

        // Validate move coordinates
        if (!board.isInBounds(row, col)) {
            return false;
        }

        // Try to place the stone
        if (!board.setCell(row, col, currentPlayer)) {
            return false;
        }

        // Record the move in history
        Move move = new Move(row, col, currentPlayer, history.size());
        history.add(move);

        // Check for win
        if (WinDetector.hasFiveInRow(board, row, col, currentPlayer)) {
            state = GameState.won(currentPlayer);
            // Do NOT toggle currentPlayer - winner remains in control
            return true;
        }

        // Check for draw (full board)
        if (isBoardFull()) {
            state = GameState.draw();
            return true;
        }

        // Continue playing - toggle to next player
        currentPlayer = currentPlayer.next();
        return true;
    }

    /**
     * Undoes the last move if there is one.
     * Removes the last Move from history, clears the board cell,
     * restores currentPlayer to that move's player, and sets state to IN_PROGRESS.
     * Returns false if history is empty, with no mutation.
     *
     * @return true if undo was successful, false otherwise
     */
    public boolean undo() {
        if (history.isEmpty()) {
            return false;
        }

        // Remove the last move
        Move lastMove = history.remove(history.size() - 1);
        
        // Clear the cell on the board
        board.clearCell(lastMove.getRow(), lastMove.getCol());
        
        // Restore the previous player
        currentPlayer = lastMove.getPlayer();
        
        // Restore game state to in progress
        state = GameState.inProgress();
        
        return true;
    }

    /**
     * Resets the game to initial state.
     * Clears all board cells, clears history, sets currentPlayer to X,
     * and state to IN_PROGRESS regardless of prior turn.
     */
    public void reset() {
        // Clear all board cells
        for (int row = 0; row < board.getSize(); row++) {
            for (int col = 0; col < board.getSize(); col++) {
                board.clearCell(row, col);
            }
        }
        
        // Clear history
        history.clear();
        
        // Reset game state
        currentPlayer = Player.X;
        state = GameState.inProgress();
    }

    /**
     * Returns an unmodifiable view of the move history.
     * Moves are in chronological order with indices consistent with append time.
     *
     * @return unmodifiable list of moves
     */
    public java.util.List<Move> getHistory() {
        return java.util.Collections.unmodifiableList(history);
    }

    /**
     * Helper method to check if the board is completely filled.
     *
     * @return true if board is full, false otherwise
     */
    private boolean isBoardFull() {
        for (int row = 0; row < board.getSize(); row++) {
            for (int col = 0; col < board.getSize(); col++) {
                if (board.isEmpty(row, col)) {
                    return false;
                }
            }
        }
        return true;
    }
}