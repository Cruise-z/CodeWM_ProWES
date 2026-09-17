cmake_minimum_required(VERSION 3.10)
project(FiveInARow)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Create the core library from source files (excluding Main.cpp)
add_library(fiveinarow_core
    src/Board.cpp
    src/Move.cpp
    src/MoveHistory.cpp
    src/WinDetector.cpp
    src/GameEngine.cpp
)

target_include_directories(fiveinarow_core PUBLIC include)

# Create the demo executable
add_executable(fiveinarow_demo src/Main.cpp)
target_link_libraries(fiveinarow_demo fiveinarow_core)

# Create the test executable
add_executable(fiveinarow_tests tests/test_main.cpp)
target_link_libraries(fiveinarow_tests fiveinarow_core)

# Enable testing
enable_testing()

# Add the test
add_test(NAME fiveinarow_test COMMAND fiveinarow_tests)