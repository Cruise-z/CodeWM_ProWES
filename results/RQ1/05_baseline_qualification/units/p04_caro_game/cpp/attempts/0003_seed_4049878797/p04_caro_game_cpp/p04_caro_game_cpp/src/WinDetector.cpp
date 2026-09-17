#include "WinDetector.h"
#include "Board.h"

namespace FiveInARow {

std::optional<Player> WinDetector::checkWin(const Board& b) {
    // Check all possible directions: horizontal, vertical, and both diagonals
    const int directions[4][2] = {{0, 1}, {1, 0}, {1, 1}, {1, -1}};
    
    for (size_t r = 0; r < b.getHeight(); ++r) {
        for (size_t c = 0; c < b.getWidth(); ++c) {
            // Skip empty cells
            CellState cell = b.get(r, c);
            if (cell == CellState::Empty) {
                continue;
            }
            
            Player player = static_cast<Player>(cell);
            
            // Check each direction for a potential five-in-a-row
            for (const auto& dir : directions) {
                int dr = dir[0];
                int dc = dir[1];
                
                // Check if we can form a five-in-a-row in this direction
                if (hasFiveFrom(b, r, c, dr, dc)) {
                    return player;
                }
            }
        }
    }
    
    // No winner found
    return std::nullopt;
}

bool WinDetector::hasFiveFrom(const Board& b, size_t r, size_t c, int dr, int dc) {
    // Get the player at the starting position
    CellState startCell = b.get(r, c);
    if (startCell == CellState::Empty) {
        return false;
    }
    
    Player player = static_cast<Player>(startCell);
    
    // Count consecutive cells of the same player in the given direction
    int count = 1;  // Start with 1 since we're counting from the starting position
    
    // Check in the forward direction
    for (int i = 1; i < 5; ++i) {
        size_t nr = r + i * dr;
        size_t nc = c + i * dc;
        
        // Check bounds
        if (!b.inBounds(nr, nc)) {
            break;
        }
        
        // Check if cell matches the player
        if (b.get(nr, nc) == startCell) {
            count++;
        } else {
            break;
        }
    }
    
    // Check in the backward direction
    for (int i = 1; i < 5; ++i) {
        size_t nr = r - i * dr;
        size_t nc = c - i * dc;
        
        // Check bounds
        if (!b.inBounds(nr, nc)) {
            break;
        }
        
        // Check if cell matches the player
        if (b.get(nr, nc) == startCell) {
            count++;
        } else {
            break;
        }
    }
    
    // We counted the starting cell twice (once in each direction),
    // so subtract one before checking if we have at least 5
    return count >= 5;
}

} // namespace FiveInARow