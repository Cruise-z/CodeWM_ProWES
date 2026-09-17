cmake_minimum_required(VERSION 3.10)
project(todo_app LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Create the core library
add_library(todo_core STATIC
    src/Task.cpp
    src/Date.cpp
    src/Query.cpp
    src/TaskStore.cpp
    src/TaskManager.cpp
)

target_include_directories(todo_core PUBLIC include)

# Create the main executable
add_executable(todo_app src/Main.cpp)
target_link_libraries(todo_app todo_core)

# Create the test executable
add_executable(todo_tests tests/test_main.cpp)
target_link_libraries(todo_tests todo_core)

# Enable testing
enable_testing()

# Add the test
add_test(NAME todo_tests COMMAND todo_tests)