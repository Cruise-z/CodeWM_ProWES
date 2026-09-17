#include "WinDetector.h"
#include "Board.h"

namespace gomoku {

std::optional<Player> WinDetector::checkWin(const Board& b) {
    // Check all directions: horizontal, vertical, and both diagonals
    const int directions[4][2] = {{0, 1}, {1, 0}, {1, 1}, {1, -1}};
    
    for (size_t r = 0; r < b.getHeight(); ++r) {
        for (size_t c = 0; c < b.getWidth(); ++c) {
            // Skip empty cells
            if (b.get(r, c) == CellState::Empty) {
                continue;
            }
            
            // Check each direction
            for (const auto& dir : directions) {
                int dr = dir[0];
                int dc = dir[1];
                
                // Check if we have at least 5 cells in this direction
                if (r + 4 * dr >= b.getHeight() || c + 4 * dc >= b.getWidth()) {
                    continue;
                }
                
                // Check if there are 5 consecutive cells of the same player
                Player currentPlayer = b.get(r, c);
                bool hasFive = true;
                
                for (int i = 1; i < 5; ++i) {
                    if (b.get(r + i * dr, c + i * dc) != currentPlayer) {
                        hasFive = false;
                        break;
                    }
                }
                
                if (hasFive) {
                    return currentPlayer;
                }
            }
        }
    }
    
    return std::nullopt;
}

bool WinDetector::hasFiveFrom(const Board& b, size_t r, size_t c, int dr, int dc) {
    // Check if starting position is valid
    if (r >= b.getHeight() || c >= b.getWidth()) {
        return false;
    }
    
    // Check if we have at least 5 cells in this direction
    if (r + 4 * dr >= b.getHeight() || c + 4 * dc >= b.getWidth()) {
        return false;
    }
    
    // Get the player at the starting position
    Player currentPlayer = b.get(r, c);
    
    // Check if there are 5 consecutive cells of the same player
    for (int i = 1; i < 5; ++i) {
        if (b.get(r + i * dr, c + i * dc) != currentPlayer) {
            return false;
        }
    }
    
    return true;
}

}  // namespace gomoku