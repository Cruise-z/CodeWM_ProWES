#include "WinDetector.h"
#include <algorithm>

namespace fiverow {

std::optional<Player> WinDetector::checkWin(const Board& b) {
    // Check all possible directions: horizontal, vertical, and both diagonals
    const int directions[4][2] = {{0, 1}, {1, 0}, {1, 1}, {1, -1}};
    
    for (int i = 0; i < 4; ++i) {
        const int dr = directions[i][0];
        const int dc = directions[i][1];
        
        // Iterate through each cell on the board
        for (size_t r = 0; r < b.getHeight(); ++r) {
            for (size_t c = 0; c < b.getWidth(); ++c) {
                // Skip empty cells
                if (b.get(r, c) == CellState::Empty) {
                    continue;
                }
                
                // Check if we can form a line of 5 in this direction
                if (hasFiveFrom(b, r, c, dr, dc)) {
                    // Return the player who made the winning move
                    return static_cast<Player>(b.get(r, c));
                }
            }
        }
    }
    
    // No winning line found
    return std::nullopt;
}

bool WinDetector::hasFiveFrom(const Board& b, size_t r, size_t c, int dr, int dc) {
    // Get the player at the starting position
    const CellState player = b.get(r, c);
    
    // Check if the starting position is empty
    if (player == CellState::Empty) {
        return false;
    }
    
    // Count consecutive cells of the same player
    int count = 1; // Start with 1 because we're counting from the initial position
    
    // Check in the positive direction
    for (int i = 1; i < 5; ++i) {
        size_t nr = r + i * static_cast<size_t>(dr);
        size_t nc = c + i * static_cast<size_t>(dc);
        
        // Check bounds
        if (!b.inBounds(nr, nc)) {
            break;
        }
        
        // Check if the cell matches the player
        if (b.get(nr, nc) != player) {
            break;
        }
        
        ++count;
    }
    
    // We need exactly 5 in a row to win
    return count >= 5;
}

}  // namespace fiverow