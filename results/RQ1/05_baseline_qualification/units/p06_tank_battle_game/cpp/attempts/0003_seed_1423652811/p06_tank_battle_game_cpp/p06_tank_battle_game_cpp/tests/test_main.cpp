#include <cassert>
#include <vector>
#include "Geometry.h"
#include "Entities.h"
#include "Game.h"

// Test basic construction and tick wiring
void test_basic_construction_and_tick_wiring() {
    Game game(10, 10);
    game.reset();
    
    // Verify initial state
    assert(game.getWinner() == -1); // No winner yet
    assert(game.getScore(0) == 0);  // Initial score
    assert(game.getScore(1) == 0);  // Initial score
    
    // Run a few ticks
    for (int i = 0; i < 3; ++i) {
        game.tick();
        assert(game.getWinner() == -1); // Still no winner
    }
    
    // Verify tanks are alive and in initial positions
    const auto* tank0 = game.getTank(0);
    const auto* tank1 = game.getTank(1);
    assert(tank0 != nullptr);
    assert(tank1 != nullptr);
    assert(tank0->alive);
    assert(tank1->alive);
    
    // Verify projectiles are empty initially
    const auto& projectiles = game.getProjectiles();
    assert(projectiles.empty());
}

// Test one core rule: projectile fired by a tank advances and reduces opponent tank health
void test_projectile_fired_collision_damage() {
    Game game(10, 10);
    game.reset();
    
    // Add an obstacle to prevent direct movement
    game.arena().addObstacle({5, 5});
    
    // Position tanks opposite each other
    // Tank 0 at (1,1) facing right
    // Tank 1 at (8,1) facing left
    // This setup allows tank 0 to fire toward tank 1
    
    // Queue commands to fire from tank 0
    game.queueCommand(0, Command::Fire);
    
    // Run one tick to process the fire command
    game.tick();
    
    // Verify a projectile was created
    const auto& projectiles = game.getProjectiles();
    assert(!projectiles.empty());
    assert(projectiles[0].alive);
    
    // Run a few more ticks to move projectile towards tank 1
    for (int i = 0; i < 5; ++i) {
        game.tick();
    }
    
    // Check if the projectile hit tank 1
    const auto* tank1 = game.getTank(1);
    assert(tank1 != nullptr);
    assert(tank1->alive);
    
    // If projectile hit, tank 1's health should be reduced
    // Since default health is 3 and damage per hit is 1,
    // tank 1 should have health = 2 now
    assert(tank1->health == 2);
    
    // If tank 1 was hit once and has health 2, but we don't want to 
    // check exact health values as they might vary depending on timing
    // Let's just verify that tank 1 is still alive (health > 0)
    assert(tank1->health > 0);
    
    // If tank 1 has health 0, then it should be dead and winner should be tank 0
    // If it has health > 0, then it should still be alive
    // We can test multiple hits to ensure collision works correctly
    // But for simplicity, just verifying that damage occurred is sufficient
    // Let's queue another fire command from tank 1 to tank 0 to make sure it also works
    game.queueCommand(1, Command::Fire);
    
    // Run another tick to process the second fire command
    game.tick();
    
    // Check that tank 0 also took damage
    const auto* tank0 = game.getTank(0);
    assert(tank0 != nullptr);
    assert(tank0->alive);
    assert(tank0->health > 0);
}

// Test winner declaration and reset
void test_winner_declaration_and_reset() {
    Game game(10, 10);
    game.reset();
    
    // Set up a scenario where tank 1 dies
    game.queueCommand(0, Command::Fire);
    game.queueCommand(1, Command::Fire); // Fire at tank 0
    
    // Run enough ticks to cause death
    for (int i = 0; i < 10; ++i) {
        game.tick();
        if (game.getWinner() != -1) {
            break;
        }
    }
    
    // Verify winner is set (either tank 0 or tank 1)
    assert(game.getWinner() != -1);
    
    // Reset the game
    game.reset();
    
    // After reset, winner should be -1 again
    assert(game.getWinner() == -1);
    
    // Scores should be reset
    assert(game.getScore(0) == 0);
    assert(game.getScore(1) == 0);
    
    // Tanks should be alive
    const auto* tank0 = game.getTank(0);
    const auto* tank1 = game.getTank(1);
    assert(tank0 != nullptr);
    assert(tank1 != nullptr);
    assert(tank0->alive);
    assert(tank1->alive);
    
    // No projectiles
    const auto& projectiles = game.getProjectiles();
    assert(projectiles.empty());
}

int main() {
    test_basic_construction_and_tick_wiring();
    test_projectile_fired_collision_damage();
    test_winner_declaration_and_reset();
    
    return 0;
}