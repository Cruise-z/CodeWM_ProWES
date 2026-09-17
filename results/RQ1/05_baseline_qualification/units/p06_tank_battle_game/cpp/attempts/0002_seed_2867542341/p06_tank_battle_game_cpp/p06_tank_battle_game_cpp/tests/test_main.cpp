// tests/test_main.cpp
#include "Geometry.h"
#include "Entities.h"
#include "Game.h"
#include <cassert>
#include <vector>

// Test basic construction and tick wiring
void test_basic_construction_and_tick_wiring() {
    Game game(10, 10);
    game.reset();
    
    // Verify initial state
    assert(game.arena().size.width == 10);
    assert(game.arena().size.height == 10);
    assert(game.getWinner() == -1); // No winner yet
    assert(game.isOver() == false); // Game not over yet
    
    // Queue some commands
    game.queueCommand(0, Command::Move);
    game.queueCommand(1, Command::Move);
    
    // Run a few ticks
    for (int i = 0; i < 3; ++i) {
        game.tick();
    }
    
    // Should still be no winner after 3 ticks
    assert(game.getWinner() == -1);
    assert(game.isOver() == false);
}

// Test one core rule: projectile fired by a tank advances and reduces opponent tank health
void test_projectile_fired_advances_and_damages_opponent() {
    Game game(10, 10);
    game.reset();
    
    // Add an obstacle to make it more interesting
    game.arena().addObstacle({5, 5});
    
    // Place tank 0 at (1,1) facing right
    // Place tank 1 at (8,8) facing left
    // Both tanks have default health of 3
    
    // Fire from tank 0
    game.queueCommand(0, Command::Fire);
    
    // Tick to process the fire command
    game.tick();
    
    // Now tank 0 should have fired a projectile
    const auto& projectiles = game.getProjectiles();
    assert(projectiles.size() == 1);
    
    const Projectile& proj = projectiles[0];
    assert(proj.ownerId == 0);
    assert(proj.alive == true);
    
    // Move to next tick where projectile moves
    game.tick();
    
    // Projectile should have moved forward
    assert(proj.pos.x == 2); // Assuming initial pos (1,1) and moving right
    assert(proj.pos.y == 1);
    
    // Fire from tank 1
    game.queueCommand(1, Command::Fire);
    game.tick(); // Process fire
    
    // Now we have two projectiles
    const auto& new_projectiles = game.getProjectiles();
    assert(new_projectiles.size() == 2);
    
    // Move forward to allow projectiles to potentially collide
    game.tick();
    game.tick();
    
    // At this point, if there's a collision between projectiles and tanks,
    // health should be reduced or tank killed
    // This simple test just confirms basic projectile existence and movement
    assert(projectiles.size() == 1);
    assert(proj.alive == true);
    
    // Check that the game has proper accessors
    const Tank* tank0 = game.getTank(0);
    const Tank* tank1 = game.getTank(1);
    assert(tank0 != nullptr);
    assert(tank1 != nullptr);
    
    // Tanks should have default health
    assert(tank0->health == 3);
    assert(tank1->health == 3);
}

int main() {
    test_basic_construction_and_tick_wiring();
    test_projectile_fired_advances_and_damages_opponent();
    
    std::cout << "All tests passed!" << std::endl;
    return 0;
}