#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Compact architecture guidance for protocol-driven project generation.

This file owns architecture quality rules, domain decomposition, coverage checks,
and language-specific repository layout guidance. It must not redefine protocol facts.
"""


ARCHITECTURE_QUALITY_INSTRUCTION = (
    "Generate a modular, domain-specific repository architecture. "
    "The file list must reflect concrete domain responsibilities, not generic software layers. "
    "Avoid broad bucket modules such as GameLogic, GameState, AppLogic, CoreLogic, StateMachine, "
    "Manager, Controller, Model, or Utils when a domain-specific file can exist. "
    "Runtime/bootstrap files should be thin. "
    "Environment-dependent code must be separated from pure/testable core logic."
)


PYTHON_ARCHITECTURE_PROFILE_INSTRUCTION = (
    "Python profile: preserve requirements.txt, Main.py, and tests/test_main.py exactly. "
    "Main.py must be a thin entrypoint. "
    "Place additional non-test modules inside a snake_case package named after the project. "
    "Use lowercase snake_case module names. "
    "For games, prefer concrete modules such as game.py, ball.py, paddle.py, brick.py, "
    "level.py, collision.py, score.py, renderer.py. "
    "Do not put most game behavior into GameLogic.py or GameState.py. "
    "If the project has four or more domain concerns, generate at least four concrete domain modules."
)


JAVA_ARCHITECTURE_PROFILE_INSTRUCTION = (
    "Java profile: preserve Maven protocol files exactly. "
    "Additional classes should normally live under src/main/java/. "
    "Prefer concrete domain classes such as Game, Ball, Paddle, Brick, Level, "
    "CollisionDetector, ScoreBoard, Renderer over GameLogic or GameState buckets."
)


CPP_ARCHITECTURE_PROFILE_INSTRUCTION = (
    "C++ profile: preserve CMakeLists.txt, src/Main.cpp, and tests/test_main.cpp exactly. "
    "Use conventional include/*.h and src/*.cpp pairs. "
    "Every non-Main src/*.cpp implementation module must have a matching include/*.h header. "
    "Every public class/function used by tests or another translation unit must be declared in include/*.h. "
    "All headers and sources must appear in File list, Canonical File References, PM Canonical File References, Logic Analysis, and Task list. "
    "tests/test_main.cpp must include headers only and must never include src/*.cpp files. "
    "CMakeLists.txt must build a core library from non-Main src/*.cpp files, link the runtime executable to that core library, "
    "link the test executable to that core library, call enable_testing(), and register the test with add_test()."
)


LANGUAGE_ARCHITECTURE_PROFILE_INSTRUCTION = (
    PYTHON_ARCHITECTURE_PROFILE_INSTRUCTION
    + " "
    + JAVA_ARCHITECTURE_PROFILE_INSTRUCTION
    + " "
    + CPP_ARCHITECTURE_PROFILE_INSTRUCTION
)


DOMAIN_REASONING_INSTRUCTION = (
    "Identify domain concerns from actual user-visible behavior, entities, rules, state transitions, "
    "correctness-critical logic, and environment-dependent boundaries. "
    "Do not start from generic layers such as Controller/Manager/Model/View."
)


DOMAIN_EXPECTATIONS_INSTRUCTION = (
    "Output 5-8 concrete domain expectations specific to the project. "
    "Each expectation should describe a real behavior, entity, rule, state transition, or boundary."
)


DOMAIN_DECOMPOSITION_INSTRUCTION = (
    "Before producing File list, decompose the project into concrete responsibilities. "
    "Output rows as [responsibility, owning_file, category]. "
    "Categories: protocol-required, package, interface, domain-entity, pure-rule, orchestration, environment-dependent, automated-test. "
    "Every non-trivial domain concern should have an owning file. "
    "Domain Decomposition must justify every non-protocol implementation file that will appear in File list. "
    "For C++ projects, include both include/*.h interface files and matching src/*.cpp implementation files. "
    "Do not output only representative responsibilities. "
    "Do not assign unrelated concerns to GameLogic/GameState/CoreLogic/StateMachine/Manager/Utils."
)


FILE_LIST_INSTRUCTION = (
    "Only output relative paths. "
    "Preserve all Protocol Contract required files exactly. "
    "Required protocol files must not be renamed, moved, replaced, or generalized. "
    "Additional non-test files may be added to improve architecture. "
    "Use exactly one protocol-level test file unless explicitly requested otherwise. "
    "For Python, add a package directory for domain modules and avoid GameLogic.py/GameState.py buckets. "
    "For C++ projects, include every include/*.h header and every matching src/*.cpp implementation file explicitly. "
    "For C++, every non-Main src/*.cpp module must have a matching include/*.h header in File list."
)


CANONICAL_FILE_REFERENCES_INSTRUCTION = (
    "Copy the complete File list exactly, item by item, in the same order. "
    "Canonical File References MUST be identical to File list. "
    "Do not summarize, filter, prioritize, shorten, deduplicate by role, or omit any file. "
    "Every path in File list must appear here exactly once. "
    "No extra paths may appear here."
)


PM_CANONICAL_FILE_REFERENCES_INSTRUCTION = (
    "Copy the complete Design stage File list exactly, item by item, in the same order. "
    "PM Canonical File References MUST equal the Design stage File list exactly. "
    "Do not summarize, filter, prioritize, shorten, deduplicate by role, or omit any file. "
    "For C++ projects, do not drop include/*.h headers when copying the Design File list."
)


IMPLEMENTATION_APPROACH_INSTRUCTION = (
    "Describe the approach in terms of protocol preservation, domain-specific architecture, "
    "thin runtime entry, core/environment separation, language conventions, and minimal automated testing. "
    "For GUI/game projects, explain how tests remain headless-friendly."
)


DOMAIN_MAPPING_INSTRUCTION = (
    "Map each core domain concern to a concrete file from Canonical File References. "
    "Prefer domain entities and pure rule modules over generic buckets. "
    "For games, map movement, collision, scoring, level/layout, rendering/input, and lifecycle separately when relevant. "
    "Cover every non-trivial domain module from File list; do not map only representative modules."
)


TESTABLE_CORE_BOUNDARY_INSTRUCTION = (
    "List pure_logic_modules, environment_dependent_modules, and test_targets_should_focus_on. "
    "Pure logic must be testable without GUI, real input devices, manual interaction, network, or OS-specific behavior. "
    "Environment-dependent modules include Main/runtime, renderer, input adapter, framework integration, network, and OS code. "
    "Include all pure domain entity/rule modules from File list, not only one representative module."
)


CPP_INTERFACE_PLAN_INSTRUCTION = (
    "For C++ projects, define uses_header_files, header_files, source_files, and test_includes_must_reference_declared_headers_only. "
    "uses_header_files must be true. "
    "Every non-Main source file in source_files must have a corresponding header in header_files. "
    "Every header in header_files must appear in File list and Canonical File References. "
    "tests/test_main.cpp must include declared headers only and must never include src/*.cpp files. "
    "For non-C++ projects, omit or leave empty."
)


TEST_INCLUDE_AUDIT_INSTRUCTION = (
    "Audit test imports/includes. "
    "Python tests may import declared package modules or protocol files. "
    "C++ tests must include only declared include/*.h headers from File list. "
    "C++ tests must not include src/*.cpp files. "
    "Report undeclared_test_includes and whether all_test_includes_declared is true."
)


PROTOCOL_COMPLIANCE_CHECK_INSTRUCTION = (
    "Audit design against Protocol Contract: build_file, runtime_entry, test_target, and test_command are preserved; "
    "required files are not missing or renamed; exactly one protocol-level test file is used; "
    "no unexpected extra test files are introduced. "
    "File list and Canonical File References must match exactly. "
    "For C++ projects, report a violation if any non-Main src/*.cpp lacks a matching include/*.h header, "
    "if tests include src/*.cpp, or if test includes reference headers absent from File list."
)


PROTOCOL_PRESERVATION_INSTRUCTION = (
    "State exact build file, runtime entry, test target, test command, and confirm exactly one protocol-level test file."
)


LOGIC_ANALYSIS_INSTRUCTION = (
    "List files with implementation responsibilities and dependencies. "
    "Use canonical relative paths only. "
    "Analyze every file in Canonical File References exactly once, not only important files. "
    "Classify each file as dependency/build, runtime/bootstrap, interface, package, domain-entity, pure-rule, orchestration, "
    "environment-dependent, or automated-test. "
    "For C++ projects, classify include/*.h files as interface/declaration files and src/*.cpp files as implementation files. "
    "Avoid generic bucket files unless narrowly justified."
)


TASK_LIST_INSTRUCTION = (
    "List implementation files in dependency-friendly order. "
    "Protocol-required files must appear first. "
    "Task list MUST contain every file from Canonical File References exactly once. "
    "Do not drop simple modules, package files, entity modules, helper modules, or files not directly tested. "
    "Use canonical relative paths only. "
    "Do not add extra test files unless requested. "
    "For C++ projects, include every required include/*.h header and every matching src/*.cpp implementation file."
)


TASK_PROTOCOL_AUDIT_INSTRUCTION = (
    "Audit PM against Protocol Contract and Design stage File list: "
    "all protocol-required files appear exactly; PM Canonical File References equals Design File list exactly; "
    "Task list contains every file from PM Canonical File References exactly once; "
    "Logic Analysis contains every file from PM Canonical File References exactly once; "
    "no required file is renamed or shortened; no undeclared file reference appears; "
    "exactly one protocol-level test file is present; no unexpected additional test files are introduced. "
    "For C++ projects, report missing headers, missing sources, or test includes that reference src/*.cpp files."
)


FILE_COVERAGE_AUDIT_INSTRUCTION = (
    "Audit file coverage across Design and PM outputs. "
    "Design File list, PM Canonical File References, Logic Analysis, and Task list should refer to the same planned files, "
    "except that Task list may reorder files. "
    "Report any file missing from PM Canonical File References, Logic Analysis, or Task list. "
    "For C++ projects, this audit must catch dropped include/*.h headers and dropped src/*.cpp implementation modules."
)


TEST_SCOPE_PLAN_INSTRUCTION = (
    "List minimal checks inside the single protocol-level test file: basic runtime wiring plus one small core rule. "
    "Avoid GUI rendering, manual interaction, network, and OS-dependent behavior."
)


TEST_INCLUDE_PLAN_INSTRUCTION = (
    "List files imported/included by the single protocol test. "
    "Use only declared canonical paths. "
    "For C++ projects, tests/test_main.cpp must include declared include/*.h headers only. "
    "Never include src/*.cpp files. "
    "Never include undeclared files."
)


MODULE_BOUNDARY_AUDIT_INSTRUCTION = (
    "Audit whether environment-dependent code leaks into pure core modules or tests. "
    "Classify every non-test implementation module from Canonical File References as core_domain_logic_modules "
    "or environment_dependent_modules. "
    "Do not classify only one representative module. "
    "Report environment_test_coupling_risks and headless_testing_risks."
)


CPP_BUILD_LINK_AUDIT_INSTRUCTION = (
    "For C++ projects, audit header/source/CMake/test build consistency. "
    "Every non-Main src/*.cpp must have a matching include/*.h. "
    "tests/test_main.cpp must include headers only and must not include src/*.cpp. "
    "CMakeLists.txt must define a reusable core library from non-Main src/*.cpp files, "
    "link the runtime executable built from src/Main.cpp against that library, "
    "link the test executable built from tests/test_main.cpp against that library, "
    "call enable_testing(), and register the test executable with add_test(). "
    "Check missing headers, undeclared includes, source/header mismatch, duplicate definitions, and likely link errors. "
    "For non-C++ projects, omit or leave empty."
)


ARCHITECTURE_COLLAPSE_AUDIT_INSTRUCTION = (
    "Audit whether architecture collapses unrelated behavior into generic bucket modules. "
    "Flag GameLogic, GameState, CoreLogic, StateMachine, Manager, Controller, Model, or Utils if they own unrelated responsibilities. "
    "For each risk, propose concrete replacements such as ball.py, collision.py, score.py, level.py, renderer.py, or equivalent domain files."
)


EXECUTION_PROTOCOL_INSTRUCTION = (
    "Specify exact test command, runtime entry, protocol test target, no manual interaction, "
    "minimal core-focused testing, exactly one protocol-level test file, and that additional files do not alter protocol files."
)


GENERIC_DOMAIN_REASONING_EXAMPLE = [
    "Core correctness depends on domain entities, rules, and state transitions.",
    "Runtime/UI concerns should be separated from testable core logic.",
]


GENERIC_DOMAIN_EXPECTATIONS_EXAMPLE = [
    "Concrete domain entities",
    "Core domain rules",
    "State transitions",
    "Result or score updates",
    "Runtime or UI boundary",
    "Minimal automated test path",
]


GENERIC_DOMAIN_DECOMPOSITION_EXAMPLE = [
    ["Runtime bootstrap", "Main.py", "protocol-required"],
    ["Game orchestration", "brick_breaker/game.py", "orchestration"],
    ["Ball movement", "brick_breaker/ball.py", "domain-entity"],
    ["Collision rules", "brick_breaker/collision.py", "pure-rule"],
    ["Protocol test", "tests/test_main.py", "automated-test"],
]


GENERIC_DOMAIN_MAPPING_EXAMPLE = [
    ["Runtime startup", "Main.py"],
    ["Game lifecycle", "brick_breaker/game.py"],
    ["Collision rules", "brick_breaker/collision.py"],
]


GENERIC_TESTABLE_CORE_BOUNDARY_EXAMPLE = {
    "pure_logic_modules": [
        "brick_breaker/ball.py",
        "brick_breaker/collision.py",
    ],
    "environment_dependent_modules": [
        "Main.py",
    ],
    "test_targets_should_focus_on": [
        "basic runtime wiring",
        "one small core rule",
    ],
}


GENERIC_TEST_SCOPE_PLAN_EXAMPLE = [
    ["tests/test_main.py", "basic runtime wiring"],
    ["tests/test_main.py", "one small core rule"],
]