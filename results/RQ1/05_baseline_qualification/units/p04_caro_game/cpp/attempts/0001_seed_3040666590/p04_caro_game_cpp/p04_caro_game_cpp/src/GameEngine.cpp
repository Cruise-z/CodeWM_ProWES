#include "GameEngine.h"
#include <stdexcept>

namespace fiverow {

GameEngine::GameEngine(size_t w, size_t h)
    : board_(w, h),
      current_player_(Player::X),
      status_(GameStatus::InProgress),
      history_() {}

const Board& GameEngine::getBoard() const noexcept {
    return board_;
}

Player GameEngine::getCurrentPlayer() const noexcept {
    return current_player_;
}

GameStatus GameEngine::getStatus() const noexcept {
    return status_;
}

const MoveHistory& GameEngine::getHistory() const noexcept {
    return history_;
}

MoveError GameEngine::applyMove(size_t r, size_t c) {
    // Check if game is already over
    if (status_ != GameStatus::InProgress) {
        return MoveError::GameOver;
    }

    // Validate coordinates
    if (!board_.inBounds(r, c)) {
        return MoveError::OutOfBounds;
    }

    // Check if cell is occupied
    if (board_.get(r, c) != CellState::Empty) {
        return MoveError::Occupied;
    }

    // Apply the move
    board_.set(r, c, static_cast<CellState>(current_player_));
    history_.push(Move(r, c, current_player_));

    // Check for win
    auto winner = WinDetector::checkWin(board_);
    if (winner.has_value()) {
        if (winner.value() == Player::X) {
            status_ = GameStatus::WonX;
        } else {
            status_ = GameStatus::WonO;
        }
        return MoveError::None;
    }

    // Check for draw
    if (board_.isFull()) {
        status_ = GameStatus::Draw;
        return MoveError::None;
    }

    // Switch players
    current_player_ = (current_player_ == Player::X) ? Player::O : Player::X;

    return MoveError::None;
}

void GameEngine::reset() {
    board_.clear();
    history_.clear();
    status_ = GameStatus::InProgress;
    current_player_ = Player::X;
}

}  // namespace fiverow