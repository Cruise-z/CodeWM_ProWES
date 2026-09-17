#include "Game.h"
#include <algorithm>
#include <cassert>

Game::Game(int32_t width, int32_t height) 
    : arena_(width, height),
      tickCount_(0),
      winnerId_(-1) {
}

void Game::reset() {
    // Clear all projectiles
    projectiles_.clear();
    
    // Clear all pending commands
    pending_.clear();
    
    // Reset tick count
    tickCount_ = 0;
    
    // Reset winner
    winnerId_ = -1;
    
    // Reset scores
    scores_.clear();
    scores_.resize(2, 0); // Two tanks with initial score 0
    
    // Create two tanks at opposite corners
    tanks_.clear();
    tanks_.emplace_back(0, Point(1, 1), Direction::Right, 3);
    tanks_.emplace_back(1, Point(8, 8), Direction::Left, 3);
}

Arena& Game::arena() {
    return arena_;
}

const Arena& Game::arena() const {
    return arena_;
}

bool Game::queueCommand(int32_t tankId, Command cmd) {
    // Validate tank ID
    if (tankId < 0 || tankId >= static_cast<int32_t>(tanks_.size())) {
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
    // Process all pending commands
    for (const auto& command : pending_) {
        int32_t tankId = command.first;
        Command cmd = command.second;
        
        // Skip dead tanks
        if (!tanks_[tankId].alive) {
            continue;
        }
        
        switch (cmd) {
            case Command::Move:
                {
                    Point newPosition = Geometry::advance(tanks_[tankId].pos, tanks_[tankId].dir);
                    
                    // Check if new position is in bounds and not an obstacle
                    if (arena_.inBounds(newPosition) && !arena_.isObstacle(newPosition)) {
                        tanks_[tankId].pos = newPosition;
                    }
                }
                break;
                
            case Command::RotateLeft:
                tanks_[tankId].rotateLeft();
                break;
                
            case Command::RotateRight:
                tanks_[tankId].rotateRight();
                break;
                
            case Command::Fire:
                {
                    // Calculate the muzzle position (front of tank)
                    Point muzzlePos = Geometry::advance(tanks_[tankId].pos, tanks_[tankId].dir);
                    
                    // Check if muzzle position is in bounds and not occupied by obstacle/tank
                    if (arena_.inBounds(muzzlePos) && !arena_.isObstacle(muzzlePos)) {
                        // Check if there's already a tank at muzzle position
                        bool tankAtMuzzle = false;
                        for (const auto& tank : tanks_) {
                            if (tank.alive && tank.pos.x == muzzlePos.x && tank.pos.y == muzzlePos.y) {
                                tankAtMuzzle = true;
                                break;
                            }
                        }
                        
                        if (!tankAtMuzzle) {
                            // Create projectile
                            projectiles_.emplace_back(tankId, muzzlePos, tanks_[tankId].dir);
                        }
                    }
                }
                break;
                
            case Command::None:
                // Do nothing
                break;
        }
    }
    
    // Clear pending commands after processing
    pending_.clear();
    
    // Update projectiles
    for (auto& projectile : projectiles_) {
        if (projectile.alive) {
            projectile.step();
            
            // Check if projectile went out of bounds
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
            for (auto& tank : tanks_) {
                if (tank.alive && tank.pos.x == projectile.pos.x && tank.pos.y == projectile.pos.y) {
                    // Hit tank
                    tank.health -= 1;
                    projectile.alive = false;
                    
                    // Check if tank died
                    if (tank.health <= 0) {
                        tank.alive = false;
                        // Award points to shooter
                        scores_[projectile.ownerId] += 1;
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
    
    // Check win condition
    int aliveTanks = 0;
    int lastAliveTankId = -1;
    
    for (size_t i = 0; i < tanks_.size(); ++i) {
        if (tanks_[i].alive) {
            aliveTanks++;
            lastAliveTankId = static_cast<int>(i);
        }
    }
    
    if (aliveTanks <= 1 && winnerId_ == -1) {
        winnerId_ = lastAliveTankId;
    }
    
    tickCount_++;
}

const Tank* Game::getTank(int32_t id) const {
    if (id < 0 || id >= static_cast<int32_t>(tanks_.size())) {
        return nullptr;
    }
    return &tanks_[id];
}

int32_t Game::getScore(int32_t id) const {
    if (id < 0 || id >= static_cast<int32_t>(scores_.size())) {
        return -1;
    }
    return scores_[id];
}

int32_t Game::getWinner() const {
    return winnerId_;
}

bool Game::isOver() const {
    return winnerId_ != -1;
}

const std::vector<Projectile>& Game::getProjectiles() const {
    return projectiles_;
}