cmake_minimum_required(VERSION 3.10)
project(FiveInARow)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Create the core library from source files (excluding Main.cpp)
add_library(fiverow_core
    src/Board.cpp
    src/Move.cpp
    src/MoveHistory.cpp
    src/WinDetector.cpp
    src/GameEngine.cpp
)

target_include_directories(fiverow_core PUBLIC include)

# Create the runtime demo executable
add_executable(fiverow_demo src/Main.cpp)
target_link_libraries(fiverow_demo fiverow_core)

# Enable testing
enable_testing()

# Create the test executable
add_executable(fiverow_tests tests/test_main.cpp)
target_link_libraries(fiverow_tests fiverow_core)

# Register the test
add_test(NAME fiverow_test COMMAND fiverow_tests)