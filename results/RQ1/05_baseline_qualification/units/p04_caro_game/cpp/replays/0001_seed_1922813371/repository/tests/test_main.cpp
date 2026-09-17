#include <cassert>
#include <iostream>
#include "GameEngine.h"
#include "Common.h"
#include "Board.h"

int main() {
    // Test 1: Basic runtime wiring via GameEngine API
    {
        gomoku::GameEngine engine;
        
        // Ensure initial status is InProgress
        assert(engine.getStatus() == gomoku::GameStatus::InProgress);
        
        // Ensure initial current player is Player::X (Alice)
        assert(engine.getCurrentPlayer() == gomoku::Player::X);
        
        // Ensure board is properly initialized
        const gomoku::Board& board = engine.getBoard();
        assert(board.getWidth() == 15);
        assert(board.getHeight() == 15);
        
        // Ensure history is empty
        assert(engine.getHistory().size() == 0);
    }
    
    // Test 2: Move validation (occupied cell rejection)
    {
        gomoku::GameEngine engine;
        
        // Make first move successfully
        auto result = engine.applyMove(7, 7);
        assert(result == gomoku::MoveError::None);
        
        // Try to make move on occupied cell
        result = engine.applyMove(7, 7);
        assert(result == gomoku::MoveError::Occupied);
    }
    
    // Test 3: Strict alternation of turns
    {
        gomoku::GameEngine engine;
        
        // Alice (X) makes first move
        auto result = engine.applyMove(7, 7);
        assert(result == gomoku::MoveError::None);
        assert(engine.getCurrentPlayer() == gomoku::Player::O);
        
        // Eve (O) makes second move
        result = engine.applyMove(7, 8);
        assert(result == gomoku::MoveError::None);
        assert(engine.getCurrentPlayer() == gomoku::Player::X);
        
        // Try to make another move as Alice (should fail)
        result = engine.applyMove(8, 8);
        assert(result == gomoku::MoveError::NotYourTurn);
    }
    
    // Test 4: Win detection for five-in-a-row (horizontal)
    {
        gomoku::GameEngine engine;
        
        // Make moves to create a horizontal five-in-a-row for X
        engine.applyMove(7, 5);  // X
        engine.applyMove(7, 6);  // O
        engine.applyMove(7, 4);  // X
        engine.applyMove(7, 7);  // O
        engine.applyMove(7, 3);  // X
        engine.applyMove(7, 8);  // O
        engine.applyMove(7, 2);  // X
        
        // Final move completes horizontal five-in-a-row for X
        auto result = engine.applyMove(7, 1);
        assert(result == gomoku::MoveError::None);
        assert(engine.getStatus() == gomoku::GameStatus::WonX);
    }
    
    // Test 5: Win detection for five-in-a-row (vertical)
    {
        gomoku::GameEngine engine;
        
        // Make moves to create a vertical five-in-a-row for O
        engine.applyMove(5, 7);  // X
        engine.applyMove(5, 6);  // O
        engine.applyMove(6, 7);  // X
        engine.applyMove(6, 6);  // O
        engine.applyMove(7, 7);  // X
        engine.applyMove(7, 6);  // O
        engine.applyMove(8, 7);  // X
        engine.applyMove(8, 6);  // O
        engine.applyMove(9, 7);  // X
        
        // Final move completes vertical five-in-a-row for O
        auto result = engine.applyMove(9, 6);
        assert(result == gomoku::MoveError::None);
        assert(engine.getStatus() == gomoku::GameStatus::WonO);
    }
    
    // Test 6: Draw detection on full board without winner
    {
        gomoku::GameEngine engine;
        
        // Fill the board with alternating moves that don't create five-in-a-row
        // We'll fill most of the board with moves that don't win
        for (size_t i = 0; i < 15; ++i) {
            for (size_t j = 0; j < 15; ++j) {
                // Skip some positions to avoid creating an immediate win
                if ((i == 7 && j == 7) || (i == 7 && j == 8) || 
                    (i == 7 && j == 9) || (i == 7 && j == 10) || 
                    (i == 7 && j == 11)) {
                    continue;
                }
                
                auto result = engine.applyMove(i, j);
                if (result != gomoku::MoveError::None) {
                    // If we can't make a move due to occupied cell or out of bounds
                    // continue to next iteration
                    continue;
                }
            }
        }
        
        // Try to make one more move to fill the board
        auto result = engine.applyMove(7, 12);
        assert(result == gomoku::MoveError::None);
        
        // Check if the board is full and game ended in a draw
        assert(engine.getStatus() == gomoku::GameStatus::Draw);
    }
    
    // Test 7: Reset restores initial state and clears history
    {
        gomoku::GameEngine engine;
        
        // Make a few moves
        engine.applyMove(7, 7);
        engine.applyMove(7, 8);
        engine.applyMove(6, 6);
        
        // Verify moves were made
        assert(engine.getHistory().size() == 3);
        assert(engine.getStatus() == gomoku::GameStatus::InProgress);
        assert(engine.getCurrentPlayer() == gomoku::Player::X);
        
        // Reset the engine
        engine.reset();
        
        // Verify reset restored initial state
        assert(engine.getHistory().size() == 0);
        assert(engine.getStatus() == gomoku::GameStatus::InProgress);
        assert(engine.getCurrentPlayer() == gomoku::Player::X);
        
        // Verify board is cleared
        const gomoku::Board& board = engine.getBoard();
        assert(board.get(7, 7) == gomoku::CellState::Empty);
        assert(board.get(7, 8) == gomoku::CellState::Empty);
        assert(board.get(6, 6) == gomoku::CellState::Empty);
    }
    
    std::cout << "All tests passed!" << std::endl;
    return 0;
}