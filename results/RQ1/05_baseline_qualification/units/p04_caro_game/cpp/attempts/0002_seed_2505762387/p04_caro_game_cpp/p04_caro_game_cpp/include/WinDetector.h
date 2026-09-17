#ifndef GOMOKU_WIN_DETECTOR_H
#define GOMOKU_WIN_DETECTOR_H

#include <optional>
#include "Board.h"

namespace gomoku {

/**
 * @brief Provides functionality to detect winning conditions in Gomoku
 * 
 * This class contains static methods to check if a player has won
 * by forming a line of five consecutive stones in any direction.
 */
class WinDetector {
public:
    /**
     * @brief Check if a player has won by forming five-in-a-row
     * 
     * @param b The board to check for a win
     * @return std::optional<Player> Player who won, or std::nullopt if no win
     */
    static std::optional<Player> checkWin(const Board& b);

    /**
     * @brief Check if there are five consecutive cells of the same player
     * starting from a given position in a specified direction
     * 
     * @param b The board to check
     * @param r Starting row index
     * @param c Starting column index
     * @param dr Row direction increment (-1, 0, or 1)
     * @param dc Column direction increment (-1, 0, or 1)
     * @return true If there are five consecutive cells of the same player
     * @return false Otherwise
     */
    static bool hasFiveFrom(const Board& b, size_t r, size_t c, int dr, int dc);
};

}  // namespace gomoku

#endif // GOMOKU_WIN_DETECTOR_H