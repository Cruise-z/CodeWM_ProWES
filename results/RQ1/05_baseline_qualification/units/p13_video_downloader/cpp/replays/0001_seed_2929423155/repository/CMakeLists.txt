cmake_minimum_required(VERSION 3.10)
project(downloader)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_EXTENSIONS OFF)

# Build the core library
add_library(downloader_core STATIC
    src/Url.cpp
    src/SafeNamer.cpp
    src/Transfer.cpp
    src/DownloadQueue.cpp
)

target_include_directories(downloader_core PUBLIC include)

# Build the application
add_executable(downloader_app src/Main.cpp)
target_link_libraries(downloader_app downloader_core)

# Build the tests
add_executable(downloader_tests tests/test_main.cpp)
target_link_libraries(downloader_tests downloader_core)

# Enable testing
enable_testing()
add_test(NAME downloader_tests COMMAND downloader_tests)