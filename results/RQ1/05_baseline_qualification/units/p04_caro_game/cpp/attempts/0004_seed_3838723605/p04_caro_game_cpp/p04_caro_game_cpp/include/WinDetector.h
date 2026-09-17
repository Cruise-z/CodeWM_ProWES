#ifndef WIN_DETECTOR_H
#define WIN_DETECTOR_H

#include <optional>
#include "Board.h"

namespace FiveInARow {

/**
 * @brief Provides functionality to detect winning conditions in a Five in a Row game
 */
class WinDetector {
public:
    /**
     * @brief Checks if there is a winner on the board
     * @param b The board to check
     * @return Player who won (Player::X or Player::O) if there's a five-in-a-row, otherwise std::nullopt
     */
    static std::optional<Player> checkWin(const Board& b);

    /**
     * @brief Checks if there are five consecutive cells of the same player starting from a given position in a specific direction
     * @param b The board to check
     * @param r Starting row index
     * @param c Starting column index
     * @param dr Row direction (-1, 0, or 1)
     * @param dc Column direction (-1, 0, or 1)
     * @return true if there are five consecutive cells of the same player in the specified direction, false otherwise
     */
    static bool hasFiveFrom(const Board& b, size_t r, size_t c, int dr, int dc);
};

}  // namespace FiveInARow

#endif // WIN_DETECTOR_H