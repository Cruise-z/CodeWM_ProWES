#include "WinDetector.h"
#include <algorithm>

namespace gomoku {

std::optional<Player> WinDetector::checkWin(const Board& b) {
    // Check all possible directions: horizontal, vertical, and both diagonals
    const int directions[4][2] = {{0, 1}, {1, 0}, {1, 1}, {1, -1}};
    
    // Iterate through each cell on the board
    for (size_t r = 0; r < b.getHeight(); ++r) {
        for (size_t c = 0; c < b.getWidth(); ++c) {
            // Skip empty cells
            CellState cell_state = b.get(r, c);
            if (cell_state == CellState::Empty) {
                continue;
            }
            
            // Check each direction for a potential five-in-a-row
            for (const auto& dir : directions) {
                int dr = dir[0];
                int dc = dir[1];
                
                // Check if we can form a sequence of 5 in this direction
                if (hasFiveFrom(b, r, c, dr, dc)) {
                    // Return the player who made the winning move
                    if (cell_state == CellState::X) {
                        return Player::X;
                    } else {
                        return Player::O;
                    }
                }
            }
        }
    }
    
    // No win detected
    return std::nullopt;
}

bool WinDetector::hasFiveFrom(const Board& b, size_t r, size_t c, int dr, int dc) {
    // Get the player who owns this cell
    CellState player_cell = b.get(r, c);
    
    // Count consecutive cells of the same player in this direction
    int count = 0;
    
    // Start from the given cell and go in the direction (dr, dc)
    size_t current_r = r;
    size_t current_c = c;
    
    // Continue while we're within bounds and the cell matches the player
    while (b.inBounds(current_r, current_c) && 
           b.get(current_r, current_c) == player_cell) {
        count++;
        
        // Move to the next cell in the direction
        current_r += dr;
        current_c += dc;
    }
    
    // We need exactly 5 consecutive cells to win
    return count >= 5;
}

} // namespace gomoku