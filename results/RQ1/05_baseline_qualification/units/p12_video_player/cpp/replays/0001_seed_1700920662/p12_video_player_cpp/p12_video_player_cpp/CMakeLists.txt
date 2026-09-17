cmake_minimum_required(VERSION 3.10)
project(video_player LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Create the core library from all src files except src/Main.cpp
file(GLOB_RECURSE CORE_SOURCES "src/*.cpp" EXCLUDE "src/Main.cpp")

add_library(video_player_lib STATIC ${CORE_SOURCES})

# Set properties for the core library
target_include_directories(video_player_lib PUBLIC include)

# Build the demo executable
add_executable(video_player_demo src/Main.cpp)
target_link_libraries(video_player_demo video_player_lib)

# Build the test executable
add_executable(video_player_tests tests/test_main.cpp)
target_link_libraries(video_player_tests video_player_lib)

# Enable testing
enable_testing()

# Add the test
add_test(NAME video_player_tests COMMAND video_player_tests)