cmake_minimum_required(VERSION 3.10)
project(Calculator)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Create the core library
add_library(calculator_core STATIC
    src/Tokens.cpp
    src/Lexer.cpp
    src/Parser.cpp
    src/Evaluator.cpp
    src/History.cpp
    src/Calculator.cpp
)

target_include_directories(calculator_core PUBLIC include)

# Create the demo executable
add_executable(calculator_demo src/Main.cpp)
target_link_libraries(calculator_demo calculator_core)

# Enable testing
enable_testing()

# Create the test executable
add_executable(calculator_test tests/test_main.cpp)
target_link_libraries(calculator_test calculator_core)

# Add the test
add_test(NAME calculator_test COMMAND calculator_test)