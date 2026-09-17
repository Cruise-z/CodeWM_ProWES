cmake_minimum_required(VERSION 3.10)
project(crud_system CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Create the core library
add_library(crud_core STATIC
    src/Record.cpp
    src/ManualClock.cpp
    src/Repository.cpp
    src/CrudService.cpp
)

# Make the include directory available to consumers
target_include_directories(crud_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)

# Create the application executable
add_executable(crud_app src/Main.cpp)
target_link_libraries(crud_app crud_core)

# Create the test executable
add_executable(crud_tests tests/test_main.cpp)
target_link_libraries(crud_tests crud_core)

# Enable testing
enable_testing()

# Register the test
add_test(NAME crud_tests COMMAND crud_tests)