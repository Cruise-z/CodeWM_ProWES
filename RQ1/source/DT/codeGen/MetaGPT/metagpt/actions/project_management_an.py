#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14 15:28
@Author  : alexanderwu
@File    : project_management_an.py
"""

from typing import List, Optional

from metagpt.actions.action_node import ActionNode
from .protocol_shared_an import (
    ARCHITECTURE_COLLAPSE_AUDIT_INSTRUCTION,
    CPP_BUILD_LINK_AUDIT_INSTRUCTION,
    EXECUTION_PROTOCOL_INSTRUCTION,
    FILE_COVERAGE_AUDIT_INSTRUCTION,
    GENERIC_TEST_SCOPE_PLAN_EXAMPLE,
    LOGIC_ANALYSIS_INSTRUCTION,
    MODULE_BOUNDARY_AUDIT_INSTRUCTION,
    PM_CANONICAL_FILE_REFERENCES_INSTRUCTION,
    TASK_LIST_INSTRUCTION,
    TASK_PROTOCOL_AUDIT_INSTRUCTION,
    TEST_INCLUDE_PLAN_INSTRUCTION,
    TEST_SCOPE_PLAN_INSTRUCTION,
)


REQUIRED_PACKAGES = ActionNode(
    key="Required packages",
    expected_type=Optional[List[str]],
    instruction=(
        "List Python third-party packages for requirements.txt. "
        "For non-Python projects, this field may be empty."
    ),
    example=[],
)


REQUIRED_OTHER_LANGUAGE_PACKAGES = ActionNode(
    key="Required Other language third-party packages",
    expected_type=List[str],
    instruction=(
        "List required non-Python build/runtime dependencies. "
        "For C++ projects, include CMake and C++ standard requirements; avoid external libraries unless requested."
    ),
    example=[
        "CMake>=3.10",
        "C++17",
        "No third-party dependencies required",
    ],
)


CANONICAL_FILE_REFERENCES = ActionNode(
    key="Canonical File References",
    expected_type=List[str],
    instruction=PM_CANONICAL_FILE_REFERENCES_INSTRUCTION,
    example=[
        "CMakeLists.txt",
        "src/Main.cpp",
        "tests/test_main.cpp",
        "include/Game.h",
        "include/Ball.h",
        "include/Paddle.h",
        "include/Brick.h",
        "include/Collision.h",
        "include/Score.h",
        "src/Game.cpp",
        "src/Ball.cpp",
        "src/Paddle.cpp",
        "src/Brick.cpp",
        "src/Collision.cpp",
        "src/Score.cpp",
    ],
)


LOGIC_ANALYSIS = ActionNode(
    key="Logic Analysis",
    expected_type=List[List[str]],
    instruction=(
        LOGIC_ANALYSIS_INSTRUCTION
        + " For C++ projects, analyze include/*.h as interface/declaration files and src/*.cpp as implementation files."
    ),
    example=[
        ["CMakeLists.txt", "dependency/build; declares core library, runtime target, and test target"],
        ["src/Main.cpp", "runtime/bootstrap; thin entrypoint"],
        ["tests/test_main.cpp", "automated-test; single protocol test"],
        ["include/Game.h", "interface; declares Game orchestration API"],
        ["include/Ball.h", "interface; declares Ball entity API"],
        ["include/Paddle.h", "interface; declares Paddle entity API"],
        ["include/Brick.h", "interface; declares Brick entity API"],
        ["include/Collision.h", "interface; declares collision rule API"],
        ["include/Score.h", "interface; declares score rule API"],
        ["src/Game.cpp", "orchestration; implements game lifecycle"],
        ["src/Ball.cpp", "domain-entity; implements ball movement"],
        ["src/Paddle.cpp", "domain-entity; implements paddle movement"],
        ["src/Brick.cpp", "domain-entity; implements brick state"],
        ["src/Collision.cpp", "pure-rule; implements collision checks"],
        ["src/Score.cpp", "pure-rule; implements scoring"],
    ],
)


REFINED_LOGIC_ANALYSIS = ActionNode(
    key="Refined Logic Analysis",
    expected_type=List[List[str]],
    instruction=(
        "Refine file responsibilities for incremental work. "
        "Use exact relative paths. "
        "No extra test files unless requested. "
        "Preserve concrete domain modules and avoid generic buckets. "
        "For C++ projects, preserve include/*.h and src/*.cpp pairs."
    ),
    example=[
        ["brick_breaker/collision.py", "update collision rules"],
        ["brick_breaker/score.py", "update score rules"],
    ],
)


TASK_LIST = ActionNode(
    key="Task list",
    expected_type=List[str],
    instruction=(
        TASK_LIST_INSTRUCTION
        + " For C++ projects, include every include/*.h header and every matching src/*.cpp implementation file. "
          "tests/test_main.cpp must include headers only and must not include src/*.cpp."
    ),
    example=[
        "CMakeLists.txt",
        "src/Main.cpp",
        "tests/test_main.cpp",
        "include/Game.h",
        "include/Ball.h",
        "include/Paddle.h",
        "include/Brick.h",
        "include/Collision.h",
        "include/Score.h",
        "src/Game.cpp",
        "src/Ball.cpp",
        "src/Paddle.cpp",
        "src/Brick.cpp",
        "src/Collision.cpp",
        "src/Score.cpp",
    ],
)


TASK_PROTOCOL_AUDIT = ActionNode(
    key="Task Protocol Audit",
    expected_type=dict,
    instruction=(
        TASK_PROTOCOL_AUDIT_INSTRUCTION
        + " For C++ projects, missing_from_task_list and missing_from_logic_analysis must report any missing include/*.h or src/*.cpp pair. "
          "undeclared_file_references must report any test include absent from PM Canonical File References or any test include of src/*.cpp."
    ),
    example={
        "required_files_present_exactly": True,
        "pm_canonical_matches_design_file_list": True,
        "task_list_covers_all_canonical_files": True,
        "logic_analysis_covers_all_canonical_files": True,
        "missing_from_pm_canonical": [],
        "missing_from_task_list": [],
        "missing_from_logic_analysis": [],
        "renamed_required_files": [],
        "noncanonical_file_references": [],
        "undeclared_file_references": [],
        "unexpected_additional_test_files": [],
    },
)


FILE_COVERAGE_AUDIT = ActionNode(
    key="File Coverage Audit",
    expected_type=dict,
    instruction=(
        FILE_COVERAGE_AUDIT_INSTRUCTION
        + " For C++ projects, this audit must catch dropped include/*.h headers and dropped src/*.cpp implementation modules."
    ),
    example={
        "design_file_list_count": 15,
        "pm_canonical_count": 15,
        "logic_analysis_count": 15,
        "task_list_count": 15,
        "missing_from_pm_canonical": [],
        "missing_from_logic_analysis": [],
        "missing_from_task_list": [],
        "extra_in_pm_canonical": [],
        "extra_in_task_list": [],
        "coverage_passed": True,
    },
)


TEST_SCOPE_PLAN = ActionNode(
    key="Test Scope Plan",
    expected_type=List[List[str]],
    instruction=TEST_SCOPE_PLAN_INSTRUCTION,
    example=[
        ["tests/test_main.cpp", "basic runtime wiring"],
        ["tests/test_main.cpp", "one small core rule"],
    ],
)


TEST_INCLUDE_PLAN = ActionNode(
    key="Test Include Plan",
    expected_type=Optional[List[List[str]]],
    instruction=(
        TEST_INCLUDE_PLAN_INSTRUCTION
        + " For C++ projects, tests/test_main.cpp must include declared include/*.h headers only. "
          "Every included header must appear in PM Canonical File References and Task list. "
          "Never include src/*.cpp files."
    ),
    example=[
        ["tests/test_main.cpp", "include/Game.h"],
        ["tests/test_main.cpp", "include/Ball.h"],
        ["tests/test_main.cpp", "include/Paddle.h"],
        ["tests/test_main.cpp", "include/Brick.h"],
        ["tests/test_main.cpp", "include/Collision.h"],
        ["tests/test_main.cpp", "include/Score.h"],
    ],
)


MODULE_BOUNDARY_AUDIT = ActionNode(
    key="Module Boundary Audit",
    expected_type=dict,
    instruction=MODULE_BOUNDARY_AUDIT_INSTRUCTION,
    example={
        "core_domain_logic_modules": [
            "src/Ball.cpp",
            "src/Paddle.cpp",
            "src/Brick.cpp",
            "src/Collision.cpp",
            "src/Score.cpp",
        ],
        "environment_dependent_modules": [
            "src/Main.cpp",
        ],
        "environment_test_coupling_risks": [],
        "headless_testing_risks": [],
    },
)


ARCHITECTURE_COLLAPSE_AUDIT = ActionNode(
    key="Architecture Collapse Audit",
    expected_type=dict,
    instruction=ARCHITECTURE_COLLAPSE_AUDIT_INSTRUCTION,
    example={
        "has_generic_bucket_modules": False,
        "generic_bucket_modules": [],
        "collapse_risks": [],
        "recommended_replacements": [],
        "passes_architecture_quality_gate": True,
    },
)


CPP_BUILD_LINK_AUDIT = ActionNode(
    key="C++ Build Link Audit",
    expected_type=Optional[dict],
    instruction=CPP_BUILD_LINK_AUDIT_INSTRUCTION,
    example={
        "declared_headers_match_declared_sources": True,
        "tests_include_headers_only": True,
        "core_library_declared": True,
        "runtime_links_core_library": True,
        "test_links_core_library": True,
        "enable_testing_declared": True,
        "add_test_declared": True,
        "missing_interface_files": [],
        "undeclared_test_includes": [],
        "suspected_build_breakers": [],
    },
)


PYTHON_DEPENDENCY_COMPATIBILITY_AUDIT = ActionNode(
    key="Python Dependency Compatibility Audit",
    expected_type=dict,
    instruction=(
        "Audit Python dependencies only. "
        "For non-Python projects, mark not_applicable=true and leave recommendations empty."
    ),
    example={
        "not_applicable": True,
        "uses_outdated_pins": False,
        "version_range_recommendations": [],
        "headless_test_notes": "",
    },
)


REFINED_TASK_LIST = ActionNode(
    key="Refined Task list",
    expected_type=List[str],
    instruction=(
        "Refine task list using exact relative paths. "
        "No extra tests unless requested. "
        "Preserve concrete domain modules and avoid generic buckets. "
        "For C++ projects, preserve include/*.h and src/*.cpp pairs."
    ),
    example=[
        "Main.py",
        "brick_breaker/collision.py",
        "brick_breaker/score.py",
        "tests/test_main.py",
    ],
)


FULL_API_SPEC = ActionNode(
    key="Full API spec",
    expected_type=str,
    instruction="OpenAPI 3.0 spec if frontend/backend API is required; otherwise blank.",
    example="",
)


SHARED_KNOWLEDGE = ActionNode(
    key="Shared Knowledge",
    expected_type=str,
    instruction=(
        "Summarize file responsibilities, imports/includes, and test boundaries using exact paths. "
        "For C++ projects, state that tests/test_main.cpp includes declared headers only and that CMake links both runtime and test targets to the core library."
    ),
    example=(
        "`tests/test_main.cpp` includes `include/Game.h`, `include/Ball.h`, and other declared headers; "
        "CMake builds a core library from src/*.cpp and links runtime/test targets to it."
    ),
)


REFINED_SHARED_KNOWLEDGE = ActionNode(
    key="Refined Shared Knowledge",
    expected_type=str,
    instruction="Update shared conventions for incremental changes using exact paths.",
    example="`brick_breaker/score.py` owns scoring and win/loss rules.",
)


EXECUTION_PROTOCOL = ActionNode(
    key="Execution Protocol",
    expected_type=str,
    instruction=(
        EXECUTION_PROTOCOL_INSTRUCTION
        + " For C++ projects, state that ctest runs the single test executable, "
          "tests/test_main.cpp includes headers only, and both runtime/test targets link against the core library."
    ),
    example=(
        "Run ctest. Runtime entry: src/Main.cpp. Test target: tests/test_main.cpp. "
        "tests/test_main.cpp includes declared headers only."
    ),
)


ANYTHING_UNCLEAR_PM = ActionNode(
    key="Anything UNCLEAR",
    expected_type=str,
    instruction="Mention unclear PM aspects if any; otherwise leave empty.",
    example="",
)


NODES = [
    REQUIRED_PACKAGES,
    REQUIRED_OTHER_LANGUAGE_PACKAGES,
    CANONICAL_FILE_REFERENCES,
    LOGIC_ANALYSIS,
    TASK_LIST,
    TASK_PROTOCOL_AUDIT,
    FILE_COVERAGE_AUDIT,
    TEST_SCOPE_PLAN,
    TEST_INCLUDE_PLAN,
    MODULE_BOUNDARY_AUDIT,
    ARCHITECTURE_COLLAPSE_AUDIT,
    CPP_BUILD_LINK_AUDIT,
    PYTHON_DEPENDENCY_COMPATIBILITY_AUDIT,
    FULL_API_SPEC,
    SHARED_KNOWLEDGE,
    EXECUTION_PROTOCOL,
    ANYTHING_UNCLEAR_PM,
]


REFINED_NODES = [
    REQUIRED_PACKAGES,
    REQUIRED_OTHER_LANGUAGE_PACKAGES,
    REFINED_LOGIC_ANALYSIS,
    REFINED_TASK_LIST,
    FULL_API_SPEC,
    REFINED_SHARED_KNOWLEDGE,
    ANYTHING_UNCLEAR_PM,
]


PM_NODE = ActionNode.from_children("PM_NODE", NODES)
REFINED_PM_NODE = ActionNode.from_children("REFINED_PM_NODE", REFINED_NODES)