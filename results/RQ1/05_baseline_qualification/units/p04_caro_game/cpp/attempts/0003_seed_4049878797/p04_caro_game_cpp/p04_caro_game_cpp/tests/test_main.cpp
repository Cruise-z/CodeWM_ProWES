#include <cassert>
#include <iostream>
#include "GameEngine.h"
#include "Common.h"
#include "Board.h"

int main() {
    // Test 1: Basic runtime wiring
    {
        FiveInARow::GameEngine engine;
        
        // Verify initial state
        assert(engine.getStatus() == FiveInARow::GameStatus::InProgress);
        assert(engine.getCurrentPlayer() == FiveInARow::Player::X);
        assert(engine.getBoard().getWidth() == 15);
        assert(engine.getBoard().getHeight() == 15);
        assert(engine.getHistory().size() == 0);
        
        std::cout << "Test 1 passed: Basic runtime wiring" << std::endl;
    }
    
    // Test 2: Move validation - occupied cell rejection
    {
        FiveInARow::GameEngine engine;
        
        // Make first move
        auto result = engine.applyMove(7, 7);
        assert(result == FiveInARow::MoveError::None);
        assert(engine.getStatus() == FiveInARow::GameStatus::InProgress);
        
        // Try to make move on occupied cell
        result = engine.applyMove(7, 7);
        assert(result == FiveInARow::MoveError::Occupied);
        assert(engine.getStatus() == FiveInARow::GameStatus::InProgress);
        
        std::cout << "Test 2 passed: Move validation - occupied cell rejection" << std::endl;
    }
    
    // Test 3: Strict alternation of turns
    {
        FiveInARow::GameEngine engine;
        
        // Alice (X) makes first move
        auto result = engine.applyMove(7, 7);
        assert(result == FiveInARow::MoveError::None);
        assert(engine.getCurrentPlayer() == FiveInARow::Player::O);
        
        // Eve (O) makes second move
        result = engine.applyMove(7, 8);
        assert(result == FiveInARow::MoveError::None);
        assert(engine.getCurrentPlayer() == FiveInARow::Player::X);
        
        // Try to make another move as X (should fail)
        result = engine.applyMove(7, 9);
        assert(result == FiveInARow::MoveError::NotYourTurn);
        assert(engine.getCurrentPlayer() == FiveInARow::Player::X);
        
        std::cout << "Test 3 passed: Strict alternation of turns" << std::endl;
    }
    
    // Test 4: Win detection for five-in-a-row (horizontal)
    {
        FiveInARow::GameEngine engine;
        
        // Play a sequence that results in a horizontal win for X
        engine.applyMove(7, 7);  // X
        engine.applyMove(7, 8);  // O
        engine.applyMove(7, 6);  // X
        engine.applyMove(7, 9);  // O
        engine.applyMove(7, 5);  // X
        engine.applyMove(7, 10); // O
        engine.applyMove(7, 4);  // X
        engine.applyMove(7, 11); // O
        engine.applyMove(7, 3);  // X
        
        // This should result in a win for X
        auto result = engine.applyMove(7, 2);  // X - creates five-in-a-row
        assert(result == FiveInARow::MoveError::None);
        assert(engine.getStatus() == FiveInARow::GameStatus::WonX);
        
        std::cout << "Test 4 passed: Win detection for five-in-a-row (horizontal)" << std::endl;
    }
    
    // Test 5: Win detection for five-in-a-row (vertical)
    {
        FiveInARow::GameEngine engine;
        
        // Play a sequence that results in a vertical win for O
        engine.applyMove(6, 7);  // X
        engine.applyMove(5, 7);  // O
        engine.applyMove(6, 6);  // X
        engine.applyMove(4, 7);  // O
        engine.applyMove(6, 5);  // X
        engine.applyMove(3, 7);  // O
        engine.applyMove(6, 4);  // X
        engine.applyMove(2, 7);  // O
        engine.applyMove(6, 3);  // X
        
        // This should result in a win for O
        auto result = engine.applyMove(1, 7);  // O - creates five-in-a-row
        assert(result == FiveInARow::MoveError::None);
        assert(engine.getStatus() == FiveInARow::GameStatus::WonO);
        
        std::cout << "Test 5 passed: Win detection for five-in-a-row (vertical)" << std::endl;
    }
    
    // Test 6: Draw detection on full board without winner
    {
        FiveInARow::GameEngine engine;
        
        // Fill board with alternating moves to create a draw
        // This is a simplified approach to fill the board without creating a win
        for (size_t i = 0; i < 15; ++i) {
            for (size_t j = 0; j < 15; ++j) {
                if ((i + j) % 2 == 0) {
                    // X plays on even positions
                    if (engine.applyMove(i, j) == FiveInARow::MoveError::None) {
                        // Continue if move was successful
                    }
                } else {
                    // O plays on odd positions
                    if (engine.applyMove(i, j) == FiveInARow::MoveError::None) {
                        // Continue if move was successful
                    }
                }
            }
        }
        
        // Check that board is full and game is drawn
        assert(engine.getBoard().isFull());
        assert(engine.getStatus() == FiveInARow::GameStatus::Draw);
        
        std::cout << "Test 6 passed: Draw detection on full board without winner" << std::endl;
    }
    
    // Test 7: Reset restores initial state and clears history
    {
        FiveInARow::GameEngine engine;
        
        // Make some moves
        engine.applyMove(7, 7);  // X
        engine.applyMove(7, 8);  // O
        engine.applyMove(7, 6);  // X
        
        // Check that game state reflects moves
        assert(engine.getHistory().size() == 3);
        assert(engine.getStatus() == FiveInARow::GameStatus::InProgress);
        assert(engine.getCurrentPlayer() == FiveInARow::Player::O);
        
        // Reset the game
        engine.reset();
        
        // Check that game is back to initial state
        assert(engine.getHistory().size() == 0);
        assert(engine.getStatus() == FiveInARow::GameStatus::InProgress);
        assert(engine.getCurrentPlayer() == FiveInARow::Player::X);
        assert(engine.getBoard().isFull() == false);
        
        std::cout << "Test 7 passed: Reset restores initial state and clears history" << std::endl;
    }
    
    std::cout << "All tests passed!" << std::endl;
    return 0;
}