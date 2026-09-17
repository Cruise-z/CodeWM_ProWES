#include "Game.h"
#include "Geometry.h"
#include <algorithm>
#include <cassert>

Game::Game(int width, int height) 
    : arena_(width, height),
      tanks_(),
      projectiles_(),
      pending_(),
      scores_(),
      tickCount_(0),
      winnerId_(-1) {
}

void Game::reset() {
    // Clear existing entities
    tanks_.clear();
    projectiles_.clear();
    pending_.clear();
    scores_.clear();
    
    // Initialize tanks at default positions
    tanks_.emplace_back(0, Point(1, 1), Direction::Right, 3);
    tanks_.emplace_back(1, Point(8, 8), Direction::Left, 3);
    
    // Initialize scores
    scores_.resize(2, 0);
    
    // Reset game state
    tickCount_ = 0;
    winnerId_ = -1;
}

Arena& Game::arena() {
    return arena_;
}

const Arena& Game::arena() const {
    return arena_;
}

bool Game::queueCommand(int tankId, Command cmd) {
    // Validate tank ID
    if (tankId < 0 || tankId >= static_cast<int>(tanks_.size())) {
        return false;
    }
    
    // Validate that tank is alive
    if (!tanks_[tankId].alive) {
        return false;
    }
    
    pending_.emplace_back(tankId, cmd);
    return true;
}

void Game::tick() {
    // Process pending commands
    for (const auto& commandPair : pending_) {
        int tankId = commandPair.first;
        Command cmd = commandPair.second;
        
        Tank& tank = tanks_[tankId];
        
        switch (cmd) {
            case Command::Move:
                {
                    Point newPos = Geometry::advance(tank.pos, tank.dir);
                    if (arena_.inBounds(newPos) && !arena_.isObstacle(newPos)) {
                        tank.pos = newPos;
                    }
                }
                break;
                
            case Command::RotateLeft:
                tank.rotateLeft();
                break;
                
            case Command::RotateRight:
                tank.rotateRight();
                break;
                
            case Command::Fire:
                {
                    Point muzzlePos = Geometry::advance(tank.pos, tank.dir);
                    if (arena_.inBounds(muzzlePos) && 
                        !arena_.isObstacle(muzzlePos) &&
                        !tank.pos.x == muzzlePos.x || !tank.pos.y == muzzlePos.y) {
                        projectiles_.emplace_back(tank.id, muzzlePos, tank.dir);
                    }
                }
                break;
                
            case Command::None:
                // Do nothing
                break;
        }
    }
    
    // Clear pending commands
    pending_.clear();
    
    // Move projectiles
    for (auto& projectile : projectiles_) {
        if (projectile.alive) {
            projectile.step();
            
            // Remove projectile if it goes out of bounds
            if (!arena_.inBounds(projectile.pos)) {
                projectile.alive = false;
                continue;
            }
            
            // Check for collisions with obstacles
            if (arena_.isObstacle(projectile.pos)) {
                projectile.alive = false;
                continue;
            }
            
            // Check for collisions with tanks
            for (auto& targetTank : tanks_) {
                if (targetTank.alive && targetTank.pos.x == projectile.pos.x && 
                    targetTank.pos.y == projectile.pos.y && 
                    targetTank.id != projectile.ownerId) {
                    // Damage the tank
                    targetTank.health--;
                    
                    // Remove the projectile
                    projectile.alive = false;
                    
                    // Check if tank is destroyed
                    if (targetTank.health <= 0) {
                        targetTank.alive = false;
                        
                        // Update score
                        scores_[projectile.ownerId]++;
                        
                        // Check for winner
                        if (winnerId_ == -1) {
                            // Check if opponent is also dead
                            int opponentId = 1 - projectile.ownerId;
                            if (!tanks_[opponentId].alive) {
                                // Both tanks dead, no winner
                                winnerId_ = -1;
                            } else {
                                // Opponent alive, declare owner as winner
                                winnerId_ = projectile.ownerId;
                            }
                        }
                    } else {
                        // Update score for hit
                        scores_[projectile.ownerId]++;
                    }
                    break;
                }
            }
        }
    }
    
    // Remove dead projectiles
    projectiles_.erase(
        std::remove_if(projectiles_.begin(), projectiles_.end(),
                       [](const Projectile& p) { return !p.alive; }),
        projectiles_.end()
    );
    
    // Update tick count
    tickCount_++;
}

const Tank* Game::getTank(int id) const {
    if (id < 0 || id >= static_cast<int>(tanks_.size())) {
        return nullptr;
    }
    return &tanks_[id];
}

int Game::getScore(int id) const {
    if (id < 0 || id >= static_cast<int>(scores_.size())) {
        return 0;
    }
    return scores_[id];
}

int Game::getWinner() const {
    return winnerId_;
}

bool Game::isOver() const {
    return winnerId_ != -1;
}

const std::vector<Projectile>& Game::getProjectiles() const {
    return projectiles_;
}