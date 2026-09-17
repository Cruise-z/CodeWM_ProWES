#include <iostream>
#include "Game.h"

int main() {
    // Create a game with a 10x10 arena
    Game game(10, 10);
    
    // Reset the game to initialize tanks and other entities
    game.reset();
    
    // Add some obstacles to the arena
    game.arena().addObstacle({3, 3});
    game.arena().addObstacle({7, 7});
    
    // Queue commands for tank 0: rotate left, move forward, fire
    game.queueCommand(0, Command::RotateLeft);
    game.queueCommand(0, Command::Move);
    game.queueCommand(0, Command::Fire);
    
    // Queue commands for tank 1: rotate right, move forward
    game.queueCommand(1, Command::RotateRight);
    game.queueCommand(1, Command::Move);
    
    // Run the game for 5 ticks
    for (int i = 0; i < 5; ++i) {
        game.tick();
        
        // Print game state after each tick
        std::cout << "Tick " << i << ":\n";
        std::cout << "  Winner: " << game.getWinner() << "\n";
        std::cout << "  Scores - Tank 0: " << game.getScore(0) 
                  << ", Tank 1: " << game.getScore(1) << "\n";
        
        // Print the positions of tanks and projectiles
        const auto* tank0 = game.getTank(0);
        const auto* tank1 = game.getTank(1);
        if (tank0 && tank0->alive) {
            std::cout << "  Tank 0: (" << tank0->pos.x << "," << tank0->pos.y 
                      << ") facing " << static_cast<int>(tank0->dir) << "\n";
        }
        if (tank1 && tank1->alive) {
            std::cout << "  Tank 1: (" << tank1->pos.x << "," << tank1->pos.y 
                      << ") facing " << static_cast<int>(tank1->dir) << "\n";
        }
        
        const auto& projectiles = game.getProjectiles();
        for (size_t j = 0; j < projectiles.size(); ++j) {
            const auto& proj = projectiles[j];
            if (proj.alive) {
                std::cout << "  Projectile " << j << ": (" << proj.pos.x << "," << proj.pos.y 
                          << ") facing " << static_cast<int>(proj.dir) << "\n";
            }
        }
        std::cout << "\n";
    }
    
    return 0;
}