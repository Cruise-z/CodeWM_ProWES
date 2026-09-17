#include <iostream>
#include "Game.h"

int main() {
    // Create game with 10x10 arena
    Game game(10, 10);
    
    // Reset game to initial state
    game.reset();
    
    // Add some obstacles
    game.arena().addObstacle({3, 3});
    game.arena().addObstacle({7, 7});
    
    // Create two tanks
    // Tank 0 at position (1,1) facing right
    game.queueCommand(0, Command::Fire);
    game.queueCommand(0, Command::Move);
    
    // Tank 1 at position (8,8) facing left
    game.queueCommand(1, Command::Fire);
    game.queueCommand(1, Command::Move);
    
    // Run 10 ticks
    for (int i = 0; i < 10; ++i) {
        game.tick();
    }
    
    // Print final state
    std::cout << "Game over. Winner: " << game.getWinner() << std::endl;
    std::cout << "Tank 0 score: " << game.getScore(0) << std::endl;
    std::cout << "Tank 1 score: " << game.getScore(1) << std::endl;
    
    return 0;
}