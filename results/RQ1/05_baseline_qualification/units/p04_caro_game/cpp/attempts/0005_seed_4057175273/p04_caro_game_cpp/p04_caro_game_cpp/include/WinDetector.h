#ifndef GOMOKU_WIN_DETECTOR_H
#define GOMOKU_WIN_DETECTOR_H

#include <optional>
#include "Board.h"

namespace gomoku {

/**
 * @brief Provides functionality for detecting winning conditions in Gomoku
 * 
 * The WinDetector class contains static methods for checking if a player has
 * achieved five consecutive stones in a row, column, or diagonal.
 */
class WinDetector {
public:
    /**
     * @brief Check if a player has won by forming five consecutive stones
     * 
     * Scans the board to determine if any player has formed a line of exactly
     * five stones horizontally, vertically, or diagonally.
     * 
     * @param b The board to check for a winning condition
     * @return std::optional<Player> Player who won if a five-in-a-row exists, otherwise std::nullopt
     */
    static std::optional<Player> checkWin(const Board& b);

    /**
     * @brief Check if there are five consecutive stones starting from a given position
     * 
     * This helper function scans in a specific direction (rowDelta, colDelta) from
     * the starting position (r, c) to see if there are exactly five stones of the same player.
     * 
     * @param b The board to scan
     * @param r Starting row index
     * @param c Starting column index
     * @param dr Row direction delta (-1, 0, or 1)
     * @param dc Column direction delta (-1, 0, or 1)
     * @return true If exactly five consecutive stones of the same player are found
     * @return false Otherwise
     */
    static bool hasFiveFrom(const Board& b, size_t r, size_t c, int dr, int dc);
};

}  // namespace gomoku

#endif // GOMOKU_WIN_DETECTOR_H