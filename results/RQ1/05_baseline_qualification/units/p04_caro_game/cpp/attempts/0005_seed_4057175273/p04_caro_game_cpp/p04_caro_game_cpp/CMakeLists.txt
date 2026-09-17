cmake_minimum_required(VERSION 3.10)
project(GomokuEngine)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Core library sources
set(CORE_SOURCES
    src/Board.cpp
    src/Move.cpp
    src/MoveHistory.cpp
    src/WinDetector.cpp
    src/GameEngine.cpp
)

# Create the core library
add_library(gomoku_core ${CORE_SOURCES})

# Include directories for the core library
target_include_directories(gomoku_core PUBLIC include)

# Demo executable
add_executable(gomoku_demo src/Main.cpp)
target_link_libraries(gomoku_demo gomoku_core)

# Test executable
add_executable(gomoku_test tests/test_main.cpp)
target_link_libraries(gomoku_test gomoku_core)

# Enable testing
enable_testing()

# Add test
add_test(NAME gomoku_test COMMAND gomoku_test)