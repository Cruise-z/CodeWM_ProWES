#include "GameEngine.h"
#include <stdexcept>

namespace gomoku {

GameEngine::GameEngine(size_t w, size_t h) 
    : board(w, h), 
      current(Player::X), 
      status(GameStatus::InProgress) {
}

const Board& GameEngine::getBoard() const noexcept {
    return board;
}

Player GameEngine::getCurrentPlayer() const noexcept {
    return current;
}

GameStatus GameEngine::getStatus() const noexcept {
    return status;
}

const MoveHistory& GameEngine::getHistory() const noexcept {
    return history;
}

MoveError GameEngine::applyMove(size_t r, size_t c) {
    // Check if game is already over
    if (status != GameStatus::InProgress) {
        return MoveError::GameOver;
    }
    
    // Validate coordinates
    if (!board.inBounds(r, c)) {
        return MoveError::OutOfBounds;
    }
    
    // Check if cell is occupied
    if (board.get(r, c) != CellState::Empty) {
        return MoveError::Occupied;
    }
    
    // Apply the move
    board.set(r, c, static_cast<CellState>(current));
    history.push(const Move(r, c, current));
    
    // Check for win
    auto winner = WinDetector::checkWin(board);
    if (winner.has_value()) {
        status = (winner.value() == Player::X) ? GameStatus::WonX : GameStatus::WonO;
        return MoveError::None;
    }
    
    // Check for draw
    if (board.isFull()) {
        status = GameStatus::Draw;
        return MoveError::None;
    }
    
    // Alternate players
    current = (current == Player::X) ? Player::O : Player::X;
    
    return MoveError::None;
}

void GameEngine::reset() {
    board.clear();
    history.clear();
    status = GameStatus::InProgress;
    current = Player::X;
}

}  // namespace gomoku