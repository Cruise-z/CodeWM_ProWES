cmake_minimum_required(VERSION 3.10)
project(FlappyBird)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Create the core library from all non-Main sources
add_library(flappy_core STATIC
    src/Random.cpp
    src/GameConfig.cpp
    src/Bird.cpp
    src/Pipe.cpp
    src/GameState.cpp
    src/GameEngine.cpp
)

# Set properties for the core library
target_include_directories(flappy_core PUBLIC include)

# Create the runtime demo executable
add_executable(flappy_demo src/Main.cpp)
target_link_libraries(flappy_demo flappy_core)

# Create the test executable
add_executable(flappy_tests tests/test_main.cpp)
target_link_libraries(flappy_tests flappy_core)

# Enable testing
enable_testing()

# Register the test
add_test(NAME flappy_tests COMMAND flappy_tests)