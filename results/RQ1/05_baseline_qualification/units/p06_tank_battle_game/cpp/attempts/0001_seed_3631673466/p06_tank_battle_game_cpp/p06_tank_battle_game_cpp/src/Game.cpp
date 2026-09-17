#include "Game.h"

Game::Game(int width, int height) 
    : arena_(width, height),
      tanks_(),
      projectiles_(),
      pending_(),
      scores_(),
      tickCount_(0),
      winnerId_(-1) {
    // Initialize tanks with default positions and directions
    tanks_.emplace_back(0, Point{1, 1}, Direction::Right);
    tanks_.emplace_back(1, Point{8, 8}, Direction::Left);
    
    // Initialize scores
    scores_.resize(2, 0);
}

void Game::reset() {
    // Reset arena
    arena_.clearObstacles();
    
    // Reset tanks to initial state
    tanks_[0].reset(Point{1, 1}, Direction::Right);
    tanks_[1].reset(Point{8, 8}, Direction::Left);
    
    // Clear projectiles
    projectiles_.clear();
    
    // Clear pending commands
    pending_.clear();
    
    // Reset scores
    scores_[0] = 0;
    scores_[1] = 0;
    
    // Reset tick count and winner
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
    if (!tanks_[tankId].alive()) {
        return false;
    }
    
    pending_.emplace_back(tankId, cmd);
    return true;
}

void Game::tick() {
    // Apply pending commands
    for (const auto& commandPair : pending_) {
        int tankId = commandPair.first;
        Command cmd = commandPair.second;
        
        Tank& tank = tanks_[tankId];
        
        switch (cmd) {
            case Command::Move:
                tank.move(arena_);
                break;
            case Command::RotateLeft:
                tank.rotateLeft();
                break;
            case Command::RotateRight:
                tank.rotateRight();
                break;
            case Command::Fire:
                // Create projectile if muzzle cell is in-bounds and free of obstacles/tanks
                Point muzzlePos = Geometry::advance(tank.pos(), tank.dir());
                if (arena_.inBounds(muzzlePos) && !arena_.isObstacle(muzzlePos)) {
                    // Check if muzzle cell is occupied by a tank
                    bool occupied = false;
                    for (const auto& otherTank : tanks_) {
                        if (otherTank.alive() && otherTank.pos() == muzzlePos) {
                            occupied = true;
                            break;
                        }
                    }
                    
                    if (!occupied) {
                        projectiles_.emplace_back(tank.id(), muzzlePos, tank.dir());
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
        projectile.step();
    }
    
    // Remove dead projectiles
    projectiles_.erase(
        std::remove_if(projectiles_.begin(), projectiles_.end(),
                       [](const Projectile& p) { return !p.alive(); }),
        projectiles_.end()
    );
    
    // Resolve collisions between projectiles and tanks
    for (auto& projectile : projectiles_) {
        if (!projectile.alive()) {
            continue;
        }
        
        Point projPos = projectile.pos();
        int ownerId = projectile.ownerId();
        
        // Check if projectile hits a tank
        for (auto& tank : tanks_) {
            if (!tank.alive()) {
                continue;
            }
            
            if (tank.pos() == projPos && tank.id() != ownerId) {
                tank.damage();
                projectile.kill();
                
                // Update score if tank died
                if (!tank.alive()) {
                    scores_[ownerId]++;
                }
                break;
            }
        }
    }
    
    // Remove dead projectiles again after potential kills
    projectiles_.erase(
        std::remove_if(projectiles_.begin(), projectiles_.end(),
                       [](const Projectile& p) { return !p.alive(); }),
        projectiles_.end()
    );
    
    // Check for winner
    int aliveCount = 0;
    int lastAliveId = -1;
    
    for (size_t i = 0; i < tanks_.size(); ++i) {
        if (tanks_[i].alive()) {
            aliveCount++;
            lastAliveId = static_cast<int>(i);
        }
    }
    
    if (aliveCount <= 1 && lastAliveId != -1) {
        winnerId_ = lastAliveId;
    }
    
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
        return -1;
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