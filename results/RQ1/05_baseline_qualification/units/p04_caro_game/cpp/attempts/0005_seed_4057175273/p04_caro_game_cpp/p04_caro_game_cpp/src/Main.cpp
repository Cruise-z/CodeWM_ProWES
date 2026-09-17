#include <iostream>
#include "GameEngine.h"

int main() {
    // Create a new game engine with default 15x15 board
    gomoku::GameEngine engine;
    
    // Print initial game state
    std::cout << "Game started with " << engine.getBoard().getWidth() 
              << "x" << engine.getBoard().getHeight() << " board." << std::endl;
    std::cout << "Current player: " << (engine.getCurrentPlayer() == gomoku::Player::X ? "X" : "O") << std::endl;
    std::cout << "Game status: " << static_cast<int>(engine.getStatus()) << std::endl;
    
    // Apply a sequence of moves demonstrating the game flow
    // Alice (X) makes first move
    auto result = engine.applyMove(7, 7);
    std::cout << "Alice (X) moves to (7,7): " << static_cast<int>(result) << std::endl;
    
    // Eve (O) makes second move
    result = engine.applyMove(7, 8);
    std::cout << "Eve (O) moves to (7,8): " << static_cast<int>(result) << std::endl;
    
    // Alice (X) makes third move
    result = engine.applyMove(6, 6);
    std::cout << "Alice (X) moves to (6,6): " << static_cast<int>(result) << std::endl;
    
    // Eve (O) makes fourth move
    result = engine.applyMove(6, 7);
    std::cout << "Eve (O) moves to (6,7): " << static_cast<int>(result) << std::endl;
    
    // Alice (X) makes fifth move
    result = engine.applyMove(5, 5);
    std::cout << "Alice (X) moves to (5,5): " << static_cast<int>(result) << std::endl;
    
    // Print final game state
    std::cout << "Final game status: " << static_cast<int>(engine.getStatus()) << std::endl;
    std::cout << "Current player: " << (engine.getCurrentPlayer() == gomoku::Player::X ? "X" : "O") << std::endl;
    
    // Print move history
    const auto& moves = engine.getHistory().all();
    std::cout << "Total moves played: " << moves.size() << std::endl;
    
    return 0;
}