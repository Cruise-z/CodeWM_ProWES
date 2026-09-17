cmake_minimum_required(VERSION 3.10)
project(PressReleaseSystem)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Core library sources (excluding Main.cpp)
set(CORE_SOURCES
    src/Clock.cpp
    src/VersionHistory.cpp
    src/TemplateEngine.cpp
    src/Validator.cpp
    src/PressRelease.cpp
    src/Renderer.cpp
    src/SearchIndex.cpp
)

# Create the core library
add_library(press_release_lib STATIC ${CORE_SOURCES})

# Include directories for the core library
target_include_directories(press_release_lib PUBLIC include)

# Runtime executable
add_executable(press_release_demo src/Main.cpp)
target_link_libraries(press_release_demo press_release_lib)

# Test executable
enable_testing()
add_executable(press_release_test tests/test_main.cpp)
target_link_libraries(press_release_test press_release_lib)
add_test(NAME press_release_test COMMAND press_release_test)