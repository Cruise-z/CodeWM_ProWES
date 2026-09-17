#ifndef FIVEROW_WINDETECTOR_H
#define FIVEROW_WINDETECTOR_H

#include "Board.h"
#include <optional>

namespace fiverow {

/**
 * @brief Provides functionality to detect winning conditions in the game
 */
class WinDetector {
public:
    /**
     * @brief Check if a player has won by getting five in a row
     * @param b The board to check
     * @return std::optional<Player> The winning player if found, otherwise std::nullopt
     */
    static std::optional<Player> checkWin(const Board& b);

    /**
     * @brief Check if there are five consecutive cells of the same player starting from a position in a direction
     * @param b The board to check
     * @param r Starting row index
     * @param c Starting column index
     * @param dr Direction change in rows (e.g., 1 for down, -1 for up, 0 for horizontal)
     * @param dc Direction change in columns (e.g., 1 for right, -1 for left, 0 for vertical)
     * @return true if five consecutive cells of the same player are found, false otherwise
     */
    static bool hasFiveFrom(const Board& b, size_t r, size_t c, int dr, int dc);
};

}  // namespace fiverow

#endif // FIVEROW_WINDETECTOR_H