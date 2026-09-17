#include "WinDetector.h"
#include <stdexcept>

namespace gomoku {

std::optional<Player> WinDetector::checkWin(const Board& b) {
    // Check all possible directions: horizontal, vertical, and both diagonals
    const int directions[4][2] = {{0, 1}, {1, 0}, {1, 1}, {1, -1}};
    
    for (size_t r = 0; r < b.getHeight(); ++r) {
        for (size_t c = 0; c < b.getWidth(); ++c) {
            // Skip empty cells
            if (b.get(r, c) == CellState::Empty) {
                continue;
            }
            
            Player currentPlayer = static_cast<Player>(b.get(r, c));
            
            // Check each direction
            for (const auto& dir : directions) {
                int dr = dir[0];
                int dc = dir[1];
                
                // Check if we can form a line of 5 in this direction
                if (hasFiveFrom(b, r, c, dr, dc)) {
                    return currentPlayer;
                }
            }
        }
    }
    
    return std::nullopt;  // No winner found
}

bool WinDetector::hasFiveFrom(const Board& b, size_t r, size_t c, int dr, int dc) {
    // Ensure we're starting from a valid position
    if (r >= b.getHeight() || c >= b.getWidth()) {
        return false;
    }
    
    // Get the player at the starting position
    CellState startState = b.get(r, c);
    if (startState == CellState::Empty) {
        return false;
    }
    
    Player startPlayer = static_cast<Player>(startState);
    
    // Check 5 consecutive positions in the specified direction
    int count = 0;
    size_t currentR = r;
    size_t currentC = c;
    
    for (int i = 0; i < 5; ++i) {
        // Check if current position is within bounds
        if (currentR >= b.getHeight() || currentC >= b.getWidth()) {
            return false;
        }
        
        // Check if the cell belongs to the same player
        if (b.get(currentR, currentC) != startState) {
            return false;
        }
        
        count++;
        
        // Move in the specified direction
        currentR += dr;
        currentC += dc;
    }
    
    // We need exactly 5 matches to form a win
    return count == 5;
}

}  // namespace gomoku