#include <iostream>
#include "Game.h"

int main() {
    // Create a game with a 10x10 arena
    Game game(10, 10);
    
    // Reset the game to initialize tanks and other state
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
    
    // Run 5 ticks of the game
    for (int i = 0; i < 5; ++i) {
        game.tick();
        
        // Print current state after each tick
        std::cout << "Tick " << i << ":\n";
        std::cout << "  Tank 0: pos(" << game.getTank(0)->pos.x << "," 
                  << game.getTank(0)->pos.y << "), health=" 
                  << game.getTank(0)->health << "\n";
        std::cout << "  Tank 1: pos(" << game.getTank(1)->pos.x << "," 
                  << game.getTank(1)->pos.y << "), health=" 
                  << game.getTank(1)->health << "\n";
        std::cout << "  Winner: " << game.getWinner() << "\n";
        std::cout << "  Scores: Tank 0=" << game.getScore(0) 
                  << ", Tank 1=" << game.getScore(1) << "\n\n";
    }
    
    return 0;
}