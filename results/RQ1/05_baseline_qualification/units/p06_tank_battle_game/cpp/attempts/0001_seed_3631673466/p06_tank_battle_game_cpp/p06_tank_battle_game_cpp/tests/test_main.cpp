#include <cassert>
#include "Geometry.h"
#include "Entities.h"
#include "Game.h"

// Test basic construction and tick wiring
void test_basic_construction_and_tick_wiring() {
    Game game(10, 10);
    game.reset();
    
    // Verify initial state
    assert(game.getTank(0) != nullptr);
    assert(game.getTank(1) != nullptr);
    assert(game.getTank(0)->id == 0);
    assert(game.getTank(1)->id == 1);
    assert(game.getTank(0)->alive == true);
    assert(game.getTank(1)->alive == true);
    assert(game.getTank(0)->health == 3);
    assert(game.getTank(1)->health == 3);
    assert(game.getWinner() == -1);
    assert(game.isOver() == false);
    
    // Run a few ticks
    for (int i = 0; i < 3; ++i) {
        game.tick();
    }
    
    // Verify state hasn't changed without commands
    assert(game.getTank(0)->pos.x == 1);
    assert(game.getTank(0)->pos.y == 1);
    assert(game.getTank(1)->pos.x == 8);
    assert(game.getTank(1)->pos.y == 8);
    assert(game.getWinner() == -1);
}

// Test movement blocked by obstacle and arena bounds
void test_movement_blocked_by_obstacle_and_bounds() {
    Game game(5, 5);
    game.reset();
    
    // Add an obstacle that blocks tank 0's path
    game.arena().addObstacle({2, 1});
    
    // Try to move tank 0 forward (should be blocked)
    game.queueCommand(0, Command::Move);
    game.tick();
    
    // Tank should not have moved due to obstacle
    assert(game.getTank(0)->pos.x == 1);
    assert(game.getTank(0)->pos.y == 1);
    
    // Try to move tank 1 forward (should be blocked by bounds)
    game.queueCommand(1, Command::Move);
    game.tick();
    
    // Tank should not have moved due to bounds
    assert(game.getTank(1)->pos.x == 8);
    assert(game.getTank(1)->pos.y == 8);
    
    // Try to rotate tank 0 left then move forward
    game.queueCommand(0, Command::RotateLeft);
    game.queueCommand(0, Command::Move);
    game.tick();
    
    // Tank should have moved left then forward
    assert(game.getTank(0)->pos.x == 1);
    assert(game.getTank(0)->pos.y == 0);  // Up one row
    
    // Try to move tank 0 right twice (should hit bounds)
    game.queueCommand(0, Command::RotateRight);
    game.queueCommand(0, Command::Move);
    game.queueCommand(0, Command::RotateRight);
    game.queueCommand(0, Command::Move);
    game.tick();
    
    // Tank should be at bottom-right corner
    assert(game.getTank(0)->pos.x == 4);
    assert(game.getTank(0)->pos.y == 0);
}

// Test projectile creation/movement and collision causing damage
void test_projectile_creation_movement_and_collision() {
    Game game(10, 10);
    game.reset();
    
    // Fire projectile from tank 0
    game.queueCommand(0, Command::Fire);
    game.tick();
    
    // Check if projectile was created
    assert(game.getProjectiles().size() == 1);
    const auto& projectile = game.getProjectiles()[0];
    assert(projectile.ownerId == 0);
    assert(projectile.alive == true);
    
    // Move projectile forward
    game.tick();
    
    // Projectile should have moved forward
    assert(projectile.pos.x == 2);  // Tank 0 starts at (1,1), facing right
    assert(projectile.pos.y == 1);
    
    // Make tank 1 move to the path of projectile
    game.queueCommand(1, Command::Move);
    game.tick();
    
    // Move projectile again
    game.tick();
    
    // Projectile should have hit tank 1
    assert(projectile.alive == false);
    assert(game.getTank(1)->health == 2);  // Damage = 1
    assert(game.getScore(0) == 1);  // Score increased
    
    // Fire another projectile from tank 1
    game.queueCommand(1, Command::Fire);
    game.tick();
    
    // Projectile should have been created
    assert(game.getProjectiles().size() == 1);
    const auto& projectile2 = game.getProjectiles()[0];
    assert(projectile2.ownerId == 1);
    
    // Move projectile to hit tank 0
    game.tick();
    game.tick();
    
    // Projectile should have hit tank 0
    assert(projectile2.alive == false);
    assert(game.getTank(0)->health == 2);
    assert(game.getScore(1) == 1);
}

// Test winner declaration and reset restoring initial state
void test_winner_declaration_and_reset() {
    Game game(10, 10);
    game.reset();
    
    // Reduce tank 0 health to 0 by firing multiple times
    game.queueCommand(0, Command::Fire);
    game.tick();
    game.tick();
    game.tick();
    game.tick();
    
    // Tank 1 should have killed tank 0
    assert(game.getTank(0)->health == 0);
    assert(game.getTank(0)->alive == false);
    assert(game.getWinner() == 1);  // Tank 1 wins
    assert(game.isOver() == true);
    
    // Reset game
    game.reset();
    
    // Check that state is restored
    assert(game.getTank(0)->health == 3);
    assert(game.getTank(1)->health == 3);
    assert(game.getTank(0)->alive == true);
    assert(game.getTank(1)->alive == true);
    assert(game.getWinner() == -1);
    assert(game.isOver() == false);
    assert(game.getScore(0) == 0);
    assert(game.getScore(1) == 0);
    assert(game.getProjectiles().size() == 0);
}

int main() {
    test_basic_construction_and_tick_wiring();
    test_movement_blocked_by_obstacle_and_bounds();
    test_projectile_creation_movement_and_collision();
    test_winner_declaration_and_reset();
    
    return 0;
}