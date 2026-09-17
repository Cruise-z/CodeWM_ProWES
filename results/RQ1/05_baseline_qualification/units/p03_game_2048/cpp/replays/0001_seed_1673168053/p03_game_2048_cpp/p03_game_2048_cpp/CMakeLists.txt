cmake_minimum_required(VERSION 3.10)
project(TwentyFortyEight)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Create the core library
add_library(twentyfortyeight_lib 
    src/Board.cpp
    src/Move.cpp
    src/Spawner.cpp
    src/Game.cpp
)

target_include_directories(twentyfortyeight_lib PUBLIC include)

# Create the runtime executable
add_executable(twentyfortyeight src/Main.cpp)
target_link_libraries(twentyfortyeight twentyfortyeight_lib)

# Create the test executable
add_executable(test_twentyfortyeight tests/test_main.cpp)
target_link_libraries(test_twentyfortyeight twentyfortyeight_lib)

# Enable testing
enable_testing()

# Add the test
add_test(NAME test_twentyfortyeight COMMAND test_twentyfortyeight)