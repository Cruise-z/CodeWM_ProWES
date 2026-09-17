cmake_minimum_required(VERSION 3.10)
project(TankBattle)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Create the core library
add_library(tankbattle_core
    src/Geometry.cpp
    src/Entities.cpp
    src/Game.cpp
)

target_include_directories(tankbattle_core PUBLIC include)

# Create the runtime executable
add_executable(tankbattle_runtime src/Main.cpp)
target_link_libraries(tankbattle_runtime tankbattle_core)

# Create the test executable
add_executable(tankbattle_test tests/test_main.cpp)
target_link_libraries(tankbattle_test tankbattle_core)

# Enable testing
enable_testing()

# Add the test to CTest
add_test(NAME tankbattle_test COMMAND tankbattle_test)