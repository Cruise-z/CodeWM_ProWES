#include <iostream>
#include "GameEngine.h"

int main() {
    // Create a new game engine with default 15x15 board
    gomoku::GameEngine engine;
    
    // Print initial game state
    std::cout << "Starting Gomoku game..." << std::endl;
    std::cout << "Initial player: " << 
        (engine.getCurrentPlayer() == gomoku::Player::X ? "X" : "O") << std::endl;
    std::cout << "Game status: " << 
        (engine.getStatus() == gomoku::GameStatus::InProgress ? "InProgress" : 
         engine.getStatus() == gomoku::GameStatus::WonX ? "WonX" : 
         engine.getStatus() == gomoku::GameStatus::WonO ? "WonO" : "Draw") << std::endl;
    
    // Apply a sequence of moves to demonstrate gameplay
    // Alice (X) makes first move
    auto result = engine.applyMove(7, 7);
    if (result != gomoku::MoveError::None) {
        std::cerr << "Failed to apply move at (7,7): " << static_cast<int>(result) << std::endl;
        return 1;
    }
    
    // Eve (O) makes second move
    result = engine.applyMove(7, 8);
    if (result != gomoku::MoveError::None) {
        std::cerr << "Failed to apply move at (7,8): " << static_cast<int>(result) << std::endl;
        return 1;
    }
    
    // Alice (X) makes third move
    result = engine.applyMove(6, 6);
    if (result != gomoku::MoveError::None) {
        std::cerr << "Failed to apply move at (6,6): " << static_cast<int>(result) << std::endl;
        return 1;
    }
    
    // Eve (O) makes fourth move
    result = engine.applyMove(6, 7);
    if (result != gomoku::MoveError::None) {
        std::cerr << "Failed to apply move at (6,7): " << static_cast<int>(result) << std::endl;
        return 1;
    }
    
    // Alice (X) makes fifth move to create a horizontal line
    result = engine.applyMove(6, 8);
    if (result != gomoku::MoveError::None) {
        std::cerr << "Failed to apply move at (6,8): " << static_cast<int>(result) << std::endl;
        return 1;
    }
    
    // Print final game state
    std::cout << "Final game status: " << 
        (engine.getStatus() == gomoku::GameStatus::InProgress ? "InProgress" : 
         engine.getStatus() == gomoku::GameStatus::WonX ? "WonX" : 
         engine.getStatus() == gomoku::GameStatus::WonO ? "WonO" : "Draw") << std::endl;
    
    // Print the winner (if any)
    if (engine.getStatus() == gomoku::GameStatus::WonX) {
        std::cout << "Winner: X (Alice)" << std::endl;
    } else if (engine.getStatus() == gomoku::GameStatus::WonO) {
        std::cout << "Winner: O (Eve)" << std::endl;
    } else if (engine.getStatus() == gomoku::GameStatus::Draw) {
        std::cout << "Game ended in a draw" << std::endl;
    }
    
    // Print move history
    std::cout << "Total moves played: " << engine.getHistory().size() << std::endl;
    
    return 0;
}