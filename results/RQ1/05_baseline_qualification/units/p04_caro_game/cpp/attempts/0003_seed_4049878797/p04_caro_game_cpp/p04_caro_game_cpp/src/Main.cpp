#include <iostream>
#include "GameEngine.h"

int main() {
    // Create a new game engine with default 15x15 board
    FiveInARow::GameEngine engine;
    
    // Print initial game state
    std::cout << "Game started with " << engine.getBoard().getWidth() 
              << "x" << engine.getBoard().getHeight() << " board." << std::endl;
    std::cout << "Current player: " << (engine.getCurrentPlayer() == FiveInARow::Player::X ? 'X' : 'O') << std::endl;
    std::cout << "Game status: " << static_cast<int>(engine.getStatus()) << std::endl;
    
    // Apply a sequence of deterministic moves
    // Alice (X) makes the first move
    auto result = engine.applyMove(7, 7);
    std::cout << "Applied move (7,7) by X: " << static_cast<int>(result) << std::endl;
    
    // Eve (O) makes the second move
    result = engine.applyMove(7, 8);
    std::cout << "Applied move (7,8) by O: " << static_cast<int>(result) << std::endl;
    
    // Alice (X) makes the third move
    result = engine.applyMove(6, 6);
    std::cout << "Applied move (6,6) by X: " << static_cast<int>(result) << std::endl;
    
    // Eve (O) makes the fourth move
    result = engine.applyMove(6, 7);
    std::cout << "Applied move (6,7) by O: " << static_cast<int>(result) << std::endl;
    
    // Alice (X) makes the fifth move to create a horizontal line
    result = engine.applyMove(5, 5);
    std::cout << "Applied move (5,5) by X: " << static_cast<int>(result) << std::endl;
    
    // Eve (O) makes the sixth move
    result = engine.applyMove(5, 6);
    std::cout << "Applied move (5,6) by O: " << static_cast<int>(result) << std::endl;
    
    // Alice (X) makes the seventh move to create a horizontal line
    result = engine.applyMove(4, 4);
    std::cout << "Applied move (4,4) by X: " << static_cast<int>(result) << std::endl;
    
    // Eve (O) makes the eighth move
    result = engine.applyMove(4, 5);
    std::cout << "Applied move (4,5) by O: " << static_cast<int>(result) << std::endl;
    
    // Alice (X) makes the ninth move to create a horizontal line
    result = engine.applyMove(3, 3);
    std::cout << "Applied move (3,3) by X: " << static_cast<int>(result) << std::endl;
    
    // Eve (O) makes the tenth move
    result = engine.applyMove(3, 4);
    std::cout << "Applied move (3,4) by O: " << static_cast<int>(result) << std::endl;
    
    // Alice (X) makes the eleventh move to form a five-in-a-row
    result = engine.applyMove(2, 2);
    std::cout << "Applied move (2,2) by X: " << static_cast<int>(result) << std::endl;
    
    // Print final game status
    std::cout << "Final game status: " << static_cast<int>(engine.getStatus()) << std::endl;
    std::cout << "Winner: " << (engine.getStatus() == FiveInARow::GameStatus::WonX ? 'X' : 
                               engine.getStatus() == FiveInARow::GameStatus::WonO ? 'O' : 'None') << std::endl;
    
    return 0;
}