#include "GameEngine.h"
#include <iostream>

int main() {
    // Create a new game engine with default 15x15 board
    fiverow::GameEngine engine;
    
    // Print initial game state
    std::cout << "Game started with " << engine.getBoard().getWidth() 
              << "x" << engine.getBoard().getHeight() << " board." << std::endl;
    std::cout << "Current player: " << (engine.getCurrentPlayer() == fiverow::Player::X ? "X" : "O") << std::endl;
    std::cout << "Game status: " << static_cast<int>(engine.getStatus()) << std::endl;
    
    // Apply a sequence of deterministic moves
    // Alice (X) makes first move
    auto result = engine.applyMove(7, 7);
    std::cout << "Applied move (7,7) by X: " << static_cast<int>(result) << std::endl;
    
    // Eve (O) makes second move
    result = engine.applyMove(7, 8);
    std::cout << "Applied move (7,8) by O: " << static_cast<int>(result) << std::endl;
    
    // Alice (X) makes third move
    result = engine.applyMove(6, 6);
    std::cout << "Applied move (6,6) by X: " << static_cast<int>(result) << std::endl;
    
    // Eve (O) makes fourth move
    result = engine.applyMove(6, 7);
    std::cout << "Applied move (6,7) by O: " << static_cast<int>(result) << std::endl;
    
    // Alice (X) makes fifth move to create a horizontal line
    result = engine.applyMove(5, 5);
    std::cout << "Applied move (5,5) by X: " << static_cast<int>(result) << std::endl;
    
    // Print final game state
    std::cout << "Final game status: " << static_cast<int>(engine.getStatus()) << std::endl;
    std::cout << "Current player: " << (engine.getCurrentPlayer() == fiverow::Player::X ? "X" : "O") << std::endl;
    
    // Print final board state (first few rows for brevity)
    const auto& board = engine.getBoard();
    std::cout << "Board state (first 5 rows):" << std::endl;
    for (size_t r = 0; r < std::min(board.getHeight(), size_t{5}); ++r) {
        for (size_t c = 0; c < std::min(board.getWidth(), size_t{5}); ++c) {
            char cell_char;
            switch (board.get(r, c)) {
                case fiverow::CellState::Empty: cell_char = '.'; break;
                case fiverow::CellState::X: cell_char = 'X'; break;
                case fiverow::CellState::O: cell_char = 'O'; break;
            }
            std::cout << cell_char << ' ';
        }
        std::cout << std::endl;
    }
    
    return 0;
}