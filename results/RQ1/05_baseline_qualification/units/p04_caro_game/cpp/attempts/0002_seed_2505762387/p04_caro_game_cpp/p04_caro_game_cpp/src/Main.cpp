#include <iostream>
#include "GameEngine.h"

int main() {
    // Create a new game engine with default 15x15 board
    gomoku::GameEngine engine;
    
    // Print initial game state
    std::cout << "Starting Gomoku game!" << std::endl;
    std::cout << "Initial player: " << (engine.getCurrentPlayer() == gomoku::Player::X ? "X" : "O") << std::endl;
    std::cout << "Game status: " << static_cast<int>(engine.getStatus()) << std::endl;
    
    // Apply a sequence of moves demonstrating the game
    // Alice (X) makes first move
    auto result = engine.applyMove(7, 7);
    std::cout << "Move (7,7) by X: " << static_cast<int>(result) << std::endl;
    
    // Eve (O) makes second move  
    result = engine.applyMove(7, 8);
    std::cout << "Move (7,8) by O: " << static_cast<int>(result) << std::endl;
    
    // Alice (X) makes third move
    result = engine.applyMove(6, 6);
    std::cout << "Move (6,6) by X: " << static_cast<int>(result) << std::endl;
    
    // Eve (O) makes fourth move
    result = engine.applyMove(6, 7);
    std::cout << "Move (6,7) by O: " << static_cast<int>(result) << std::endl;
    
    // Alice (X) makes fifth move
    result = engine.applyMove(5, 5);
    std::cout << "Move (5,5) by X: " << static_cast<int>(result) << std::endl;
    
    // Print final game state
    std::cout << "Final game status: " << static_cast<int>(engine.getStatus()) << std::endl;
    std::cout << "Current player: " << (engine.getCurrentPlayer() == gomoku::Player::X ? "X" : "O") << std::endl;
    
    return 0;
}