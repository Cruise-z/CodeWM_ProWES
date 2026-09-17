/**
 * Pure rule for detecting if a move results in a win.
 * Implements four-direction two-sided count for five-in-a-row.
 */
public final class WinDetector {
    
    /**
     * Checks if placing a stone at the given position results in a win.
     * Counts contiguous stones including the just-placed stone in all four directions:
     * horizontal (0,1), vertical (1,0), diagonal (1,1), anti-diagonal (1,-1).
     * If any direction has 5 or more contiguous stones, returns true.
     *
     * @param board the game board
     * @param row the row of the newly placed stone
     * @param col the column of the newly placed stone
     * @param player the player who placed the stone
     * @return true if the move results in a win, false otherwise
     */
    public static boolean hasFiveInRow(Board board, int row, int col, Player player) {
        // Check all four directions: horizontal, vertical, diagonal, anti-diagonal
        int[][] directions = {{0, 1}, {1, 0}, {1, 1}, {1, -1}};
        
        for (int[] dir : directions) {
            int count = 1; // Count the placed stone itself
            
            // Check in positive direction
            int r = row + dir[0];
            int c = col + dir[1];
            while (board.isInBounds(r, c) && board.getCell(r, c) == player) {
                count++;
                r += dir[0];
                c += dir[1];
            }
            
            // Check in negative direction
            r = row - dir[0];
            c = col - dir[1];
            while (board.isInBounds(r, c) && board.getCell(r, c) == player) {
                count++;
                r -= dir[0];
                c -= dir[1];
            }
            
            // If we found 5 or more contiguous stones, we have a win
            if (count >= 5) {
                return true;
            }
        }
        
        return false;
    }
}