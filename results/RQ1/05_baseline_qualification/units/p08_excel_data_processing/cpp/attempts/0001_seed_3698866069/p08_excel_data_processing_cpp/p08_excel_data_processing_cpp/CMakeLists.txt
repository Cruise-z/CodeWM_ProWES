cmake_minimum_required(VERSION 3.10)
project(excelcore LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Create the core library
add_library(excelcore STATIC
    src/ExcelCore.cpp
    src/ExcelOps.cpp
)

target_include_directories(excelcore PUBLIC include)

# Create the demo executable
add_executable(excel_demo src/Main.cpp)
target_link_libraries(excel_demo excelcore)

# Create the test executable
add_executable(excel_tests tests/test_main.cpp)
target_link_libraries(excel_tests excelcore)

# Enable testing
enable_testing()
add_test(NAME excel_tests COMMAND excel_tests)