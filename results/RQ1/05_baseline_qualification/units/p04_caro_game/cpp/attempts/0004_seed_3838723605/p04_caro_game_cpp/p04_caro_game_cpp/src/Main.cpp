#include "GameEngine.h"
#include <iostream>

int main() {
    // Create a new game engine with default 15x15 board
    FiveInARow::GameEngine game;
    
    // Print initial game state
    std::cout << "Game started! Current player: " 
              << (game.getCurrentPlayer() == FiveInARow::Player::X ? "X" : "O") 
              << std::endl;
    
    // Apply a sequence of moves demonstrating the game
    // Alice (X) makes first move
    auto error = game.applyMove(7, 7);
    if (error != FiveInARow::MoveError::None) {
        std::cerr << "Error applying move: " << static_cast<int>(error) << std::endl;
        return 1;
    }
    
    // Eve (O) makes second move
    error = game.applyMove(7, 8);
    if (error != FiveInARow::MoveError::None) {
        std::cerr << "Error applying move: " << static_cast<int>(error) << std::endl;
        return 1;
    }
    
    // Alice (X) makes third move
    error = game.applyMove(6, 6);
    if (error != FiveInARow::MoveError::None) {
        std::cerr << "Error applying move: " << static_cast<int>(error) << std::endl;
        return 1;
    }
    
    // Eve (O) makes fourth move
    error = game.applyMove(6, 7);
    if (error != FiveInARow::MoveError::None) {
        std::cerr << "Error applying move: " << static_cast<int>(error) << std::endl;
        return 1;
    }
    
    // Alice (X) makes fifth move - creating a horizontal line of 5
    error = game.applyMove(5, 5);
    if (error != FiveInARow::MoveError::None) {
        std::cerr << "Error applying move: " << static_cast<int>(error) << std::endl;
        return 1;
    }
    
    // Print final game state
    std::cout << "Game status: ";
    switch (game.getStatus()) {
        case FiveInARow::GameStatus::InProgress:
            std::cout << "IN PROGRESS";
            break;
        case FiveInARow::GameStatus::WonX:
            std::cout << "X WINS";
            break;
        case FiveInARow::GameStatus::WonO:
            std::cout << "O WINS";
            break;
        case FiveInARow::GameStatus::Draw:
            std::cout << "DRAW";
            break;
    }
    std::cout << std::endl;
    
    // Print move history
    std::cout << "Moves played: " << game.getHistory().size() << std::endl;
    
    return 0;
}