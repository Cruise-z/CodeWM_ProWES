cmake_minimum_required(VERSION 3.10)
project(SnakeGame)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Create the core library
add_library(snake_core 
    src/Random.cpp
    src/Board.cpp
    src/Snake.cpp
    src/Game.cpp
)

target_include_directories(snake_core PUBLIC 
    $<INSTALL_INTERFACE:include>
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

# Runtime executable
add_executable(snake_runtime src/Main.cpp)
target_link_libraries(snake_runtime snake_core)

# Test executable
add_executable(snake_tests tests/test_main.cpp)
target_link_libraries(snake_tests snake_core)

# Enable testing
enable_testing()

# Add test
add_test(NAME snake_test COMMAND snake_tests)