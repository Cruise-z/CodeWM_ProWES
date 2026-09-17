# CMakeLists.txt
cmake_minimum_required(VERSION 3.10)
project(TankGame)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Core library sources
set(CORE_SOURCES
    src/Geometry.cpp
    src/Entities.cpp
    src/Game.cpp
)

# Create core library
add_library(tankgame_core STATIC ${CORE_SOURCES})

# Include directories for the core library
target_include_directories(tankgame_core PUBLIC include)

# Runtime executable
add_executable(tankgame_runtime src/Main.cpp)
target_link_libraries(tankgame_runtime tankgame_core)

# Test executable
add_executable(tankgame_test tests/test_main.cpp)
target_link_libraries(tankgame_test tankgame_core)

# Enable testing
enable_testing()

# Add test
add_test(NAME tankgame_test COMMAND tankgame_test)