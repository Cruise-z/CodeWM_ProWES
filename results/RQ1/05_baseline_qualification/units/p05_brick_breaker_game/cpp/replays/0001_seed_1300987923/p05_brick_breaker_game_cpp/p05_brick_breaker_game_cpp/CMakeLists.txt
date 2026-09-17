cmake_minimum_required(VERSION 3.10)
project(Breakout)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Create the core static library
add_library(breakout_core STATIC
    src/Vector2.cpp
    src/Ball.cpp
    src/Paddle.cpp
    src/Brick.cpp
    src/Level.cpp
    src/Collision.cpp
    src/Playfield.cpp
    src/GameEngine.cpp
)

# Set properties for the core library
target_include_directories(breakout_core PUBLIC include)

# Create the runtime executable
add_executable(breakout_runtime src/Main.cpp)
target_link_libraries(breakout_runtime breakout_core)

# Create the test executable
add_executable(breakout_test tests/test_main.cpp)
target_link_libraries(breakout_test breakout_core)

# Enable testing
enable_testing()

# Add the test
add_test(NAME breakout_test COMMAND breakout_test)