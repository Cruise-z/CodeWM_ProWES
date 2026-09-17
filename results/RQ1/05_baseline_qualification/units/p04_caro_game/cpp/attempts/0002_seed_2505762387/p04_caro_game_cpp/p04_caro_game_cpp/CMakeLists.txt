cmake_minimum_required(VERSION 3.10)
project(GomokuEngine)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Create the core library from domain source files
add_library(gomoku_core STATIC
    src/Board.cpp
    src/Move.cpp
    src/MoveHistory.cpp
    src/WinDetector.cpp
    src/GameEngine.cpp
)

# Set include directories for the core library
target_include_directories(gomoku_core PUBLIC
    $<TARGET_PROPERTY:gomoku_core,INCLUDE_DIRECTORIES>
    include
)

# Create the demo executable
add_executable(gomoku_demo src/Main.cpp)
target_link_libraries(gomoku_demo gomoku_core)

# Enable testing
enable_testing()

# Create the test executable
add_executable(gomoku_test tests/test_main.cpp)
target_link_libraries(gomoku_test gomoku_core)

# Register the test
add_test(NAME gomoku_test COMMAND gomoku_test)