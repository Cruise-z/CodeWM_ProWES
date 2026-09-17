cmake_minimum_required(VERSION 3.10)
project(GomokuEngine)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Create the core library from domain source files
add_library(gomoku_core
    src/Board.cpp
    src/Move.cpp
    src/MoveHistory.cpp
    src/WinDetector.cpp
    src/GameEngine.cpp
)

# Set include directories for the core library
target_include_directories(gomoku_core PUBLIC include)

# Create the runtime demo executable
add_executable(gomoku_demo src/Main.cpp)
target_link_libraries(gomoku_demo gomoku_core)

# Enable testing
enable_testing()

# Create the test executable
add_executable(gomoku_tests tests/test_main.cpp)
target_link_libraries(gomoku_tests gomoku_core)

# Register the test
add_test(NAME gomoku_test COMMAND gomoku_tests)