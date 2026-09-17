#ifndef WIN_DETECTOR_H
#define WIN_DETECTOR_H

#include <optional>
#include "Board.h"

namespace FiveInARow {

/**
 * @brief Provides functionality to detect winning conditions in the game
 */
class WinDetector {
public:
    /**
     * @brief Check if a player has won by forming five consecutive cells
     * @param b The board to check
     * @return std::optional<Player> Player who won, or std::nullopt if no winner
     */
    static std::optional<Player> checkWin(const Board& b);

    /**
     * @brief Check if there are five consecutive cells of the same player starting from (r,c) in direction (dr,dc)
     * @param b The board to check
     * @param r Starting row
     * @param c Starting column
     * @param dr Row direction (-1, 0, or 1)
     * @param dc Column direction (-1, 0, or 1)
     * @return bool True if five consecutive cells are found, false otherwise
     */
    static bool hasFiveFrom(const Board& b, size_t r, size_t c, int dr, int dc);
};

} // namespace FiveInARow

#endif // WIN_DETECTOR_H