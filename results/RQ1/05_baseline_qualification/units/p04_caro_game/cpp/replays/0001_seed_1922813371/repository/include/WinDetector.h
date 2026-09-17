#ifndef GOMOKU_WIN_DETECTOR_H
#define GOMOKU_WIN_DETECTOR_H

#include <optional>
#include "Board.h"

namespace gomoku {

/**
 * @brief Provides functionality to detect winning conditions in Gomoku
 * 
 * The WinDetector class contains static methods to check if a player has
 * achieved five-in-a-row on the board in any direction (horizontal, vertical,
 * or diagonal).
 */
class WinDetector {
public:
    /**
     * @brief Check if a player has won by forming five-in-a-row
     * 
     * This method examines the board to determine if any player has formed
     * a continuous line of five or more stones in any of the four directions:
     * horizontal, vertical, and both diagonals.
     * 
     * @param b The board to check for a win
     * @return std::optional<Player> The winning player if a five-in-a-row exists,
     *         otherwise std::nullopt
     */
    static std::optional<Player> checkWin(const Board& b);

    /**
     * @brief Check if there are five consecutive cells of the same player
     * starting from a given position in a specific direction
     * 
     * This helper method scans the board in a specified direction (dr, dc)
     * from the starting position (r, c) to see if there are exactly five
     * consecutive cells belonging to the same player.
     * 
     * @param b The board to scan
     * @param r Starting row index
     * @param c Starting column index
     * @param dr Row direction increment (-1, 0, or 1)
     * @param dc Column direction increment (-1, 0, or 1)
     * @return true if exactly five consecutive cells of the same player exist
     *         in the specified direction, false otherwise
     */
    static bool hasFiveFrom(const Board& b, size_t r, size_t c, int dr, int dc);
};

} // namespace gomoku

#endif // GOMOKU_WIN_DETECTOR_H