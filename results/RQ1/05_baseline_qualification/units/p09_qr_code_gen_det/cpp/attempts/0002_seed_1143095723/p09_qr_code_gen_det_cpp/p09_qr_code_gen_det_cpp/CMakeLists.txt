cmake_minimum_required(VERSION 3.10)
project(qr_code_project LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Create the qr_core library
add_library(qr_core STATIC
    src/QRMatrix.cpp
    src/QRCodec.cpp
    src/QRRenderer.cpp
)

# Publish the include directory
target_include_directories(qr_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)

# Create the qr_app executable
add_executable(qr_app src/Main.cpp)
target_link_libraries(qr_app qr_core)

# Create the qr_tests executable
add_executable(qr_tests tests/test_main.cpp)
target_link_libraries(qr_tests qr_core)

# Enable testing
enable_testing()
add_test(NAME qr_tests COMMAND qr_tests)