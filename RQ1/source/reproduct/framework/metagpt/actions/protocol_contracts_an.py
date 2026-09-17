#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Protocol contracts for Java / Python / C++ project generation.

This file owns only stable protocol facts:
- build file
- runtime entry
- protocol test target
- test command
- required files

Architecture quality guidance belongs in architecture_guidance_an.py.
"""


LANGUAGE_PROTOCOLS = {
    "Java": {
        "build_file": "pom.xml",
        "runtime_entry": "src/main/java/Main.java",
        "test_target": "src/test/java/MainTest.java",
        "test_command": "mvn test",
        "required_files_exact": [
            "pom.xml",
            "src/main/java/Main.java",
            "src/test/java/MainTest.java",
        ],
    },
    "Python": {
        "build_file": "requirements.txt",
        "runtime_entry": "Main.py",
        "test_target": "tests/test_main.py",
        "test_command": "pytest",
        "required_files_exact": [
            "requirements.txt",
            "Main.py",
            "tests/test_main.py",
        ],
    },
    "C++": {
        "build_file": "CMakeLists.txt",
        "runtime_entry": "src/Main.cpp",
        "test_target": "tests/test_main.cpp",
        "test_command": "ctest",
        "required_files_exact": [
            "CMakeLists.txt",
            "src/Main.cpp",
            "tests/test_main.cpp",
        ],
    },
}


PROTOCOL_INVARIANTS = (
    "Protocol files are normative and override any preferred project structure. "
    "Follow only the protocol for the selected language. "
    "<Java protocol>: build_file=pom.xml; runtime_entry=src/main/java/Main.java; test_target=src/test/java/MainTest.java; test_command=mvn test; required_files_exact=[pom.xml, src/main/java/Main.java, src/test/java/MainTest.java]. "
    "<Python protocol>: build_file=requirements.txt; runtime_entry=Main.py; test_target=tests/test_main.py; test_command=pytest; required_files_exact=[requirements.txt, Main.py, tests/test_main.py]. "
    "<C++ protocol>: build_file=CMakeLists.txt; runtime_entry=src/Main.cpp; test_target=tests/test_main.cpp; test_command=ctest; required_files_exact=[CMakeLists.txt, src/Main.cpp, tests/test_main.cpp]. "
    "Do not generate an alternative build file, runtime entry, or test target. "
    "Do not rename, omit, move, replace, generalize, or reinterpret any required exact file. "
    "Additional source files are allowed only if all required exact files remain present and valid. "
    "The project must build and pass tests using the specified test_command."
)


INTERFACE_PROTOCOL_INSTRUCTION = (
    "Select the exact protocol for the requested programming language from following supported contracts. "
    "Output build_file, runtime_entry, test_target, test_command, and required_files_exact. "
    + PROTOCOL_INVARIANTS
)


GENERAL_TESTING_CONSTRAINTS_INSTRUCTION = (
    "Use exactly one minimal protocol-level test file. "
    "Do not add extra test files unless explicitly requested. "
    "Tests must be automated, deterministic, headless-friendly, and must not require manual interaction, "
    "GUI rendering, real input devices, network access, or OS-specific behavior. "
    "The test should cover basic runtime wiring plus one small runtime-relevant core rule."
)


LANGUAGE_CONVENTION_REQUIREMENTS_INSTRUCTION = (
    "Follow language conventions without changing protocol files. "
    "Java uses Maven layout. "
    "Python keeps Main.py thin and places extra non-test modules in a snake_case package. "
    "C++ uses CMake, src/, tests/, and include/. "
    "For C++ projects, use conventional include/*.h and src/*.cpp pairs. "
    "Every non-Main src/*.cpp module that exposes classes or functions to another file must have a matching include/*.h header. "
    "tests/test_main.cpp must include headers only and must not include src/*.cpp implementation files."
)