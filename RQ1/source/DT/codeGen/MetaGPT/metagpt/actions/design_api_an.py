#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/12 22:24
@Author  : alexanderwu
@File    : design_api_an.py
"""

from typing import List, Optional

from metagpt.actions.action_node import ActionNode
from metagpt.utils.mermaid import MMC1, MMC2
from .protocol_shared_an import (
    ARCHITECTURE_QUALITY_INSTRUCTION,
    CANONICAL_FILE_REFERENCES_INSTRUCTION,
    CPP_INTERFACE_PLAN_INSTRUCTION,
    DOMAIN_DECOMPOSITION_INSTRUCTION,
    DOMAIN_MAPPING_INSTRUCTION,
    FILE_LIST_INSTRUCTION,
    GENERIC_DOMAIN_DECOMPOSITION_EXAMPLE,
    GENERIC_TESTABLE_CORE_BOUNDARY_EXAMPLE,
    IMPLEMENTATION_APPROACH_INSTRUCTION,
    LANGUAGE_ARCHITECTURE_PROFILE_INSTRUCTION,
    PROTOCOL_COMPLIANCE_CHECK_INSTRUCTION,
    PROTOCOL_PRESERVATION_INSTRUCTION,
    TESTABLE_CORE_BOUNDARY_INSTRUCTION,
    TEST_INCLUDE_AUDIT_INSTRUCTION,
)


IMPLEMENTATION_APPROACH = ActionNode(
    key="Implementation approach",
    expected_type=str,
    instruction=(
        IMPLEMENTATION_APPROACH_INSTRUCTION
        + " "
        + ARCHITECTURE_QUALITY_INSTRUCTION
        + " "
        + LANGUAGE_ARCHITECTURE_PROFILE_INSTRUCTION
    ),
    example=(
        "Preserve protocol files exactly. Keep runtime entry thin. Split concrete domain entities/rules "
        "into separate modules and keep one minimal headless-friendly protocol test."
    ),
)


REFINED_IMPLEMENTATION_APPROACH = ActionNode(
    key="Refined Implementation Approach",
    expected_type=str,
    instruction=(
        "Update the approach for incremental requirements. Preserve protocol files, existing good boundaries, "
        "and concrete domain modules. Avoid introducing generic bucket modules."
    ),
    example="Refine existing modules while preserving protocol and architecture boundaries.",
)


PROJECT_NAME = ActionNode(
    key="Project name",
    expected_type=str,
    instruction="Project name in snake_case.",
    example="brick_breaker_game",
)


DOMAIN_DECOMPOSITION = ActionNode(
    key="Domain Decomposition",
    expected_type=List[List[str]],
    instruction=(
        DOMAIN_DECOMPOSITION_INSTRUCTION
        + " For C++ projects, plan include/*.h interface files together with matching src/*.cpp implementation files."
    ),
    example=GENERIC_DOMAIN_DECOMPOSITION_EXAMPLE,
)


FILE_LIST = ActionNode(
    key="File list",
    expected_type=List[str],
    instruction=(
        FILE_LIST_INSTRUCTION
        + " For C++ projects, include CMakeLists.txt, src/Main.cpp, tests/test_main.cpp, "
          "all include/*.h headers, and all matching src/*.cpp implementation files."
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


CANONICAL_FILE_REFERENCES = ActionNode(
    key="Canonical File References",
    expected_type=List[str],
    instruction=CANONICAL_FILE_REFERENCES_INSTRUCTION,
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


REFINED_FILE_LIST = ActionNode(
    key="Refined File list",
    expected_type=List[str],
    instruction=(
        "Update the file list for incremental work. Keep protocol-required files exact. "
        "Add only needed non-test files. Do not add extra test files unless requested. "
        "Avoid generic bucket modules. "
        "For C++ projects, preserve include/*.h and src/*.cpp pairs."
    ),
    example=[
        "Main.py",
        "brick_breaker/game.py",
        "brick_breaker/collision.py",
        "tests/test_main.py",
    ],
)


DATA_STRUCTURES_AND_INTERFACES = ActionNode(
    key="Data structures and interfaces",
    expected_type=Optional[str],
    instruction=(
        "Use mermaid classDiagram syntax. Include concrete domain classes, major methods/functions, "
        "and relationships. Avoid generic bucket classes."
    ),
    example=MMC1,
)


REFINED_DATA_STRUCTURES_AND_INTERFACES = ActionNode(
    key="Refined Data structures and interfaces",
    expected_type=str,
    instruction="Update the classDiagram for incremental changes while preserving valid existing design.",
    example=MMC1,
)


PROGRAM_CALL_FLOW = ActionNode(
    key="Program call flow",
    expected_type=Optional[str],
    instruction=(
        "Use mermaid sequenceDiagram syntax. Show runtime entry delegating to orchestration, "
        "domain entities, pure rules, and environment adapters when relevant."
    ),
    example=MMC2,
)


REFINED_PROGRAM_CALL_FLOW = ActionNode(
    key="Refined Program call flow",
    expected_type=str,
    instruction="Update the sequenceDiagram for incremental changes while preserving valid existing flow.",
    example=MMC2,
)


DOMAIN_MAPPING = ActionNode(
    key="Domain Mapping",
    expected_type=List[List[str]],
    instruction=(
        DOMAIN_MAPPING_INSTRUCTION
        + " Use exact paths from Canonical File References only."
    ),
    example=[
        ["Runtime startup", "Main.py"],
        ["Package initialization", "brick_breaker/__init__.py"],
        ["Game orchestration", "brick_breaker/game.py"],
        ["Ball movement and bounce behavior", "brick_breaker/ball.py"],
        ["Paddle movement and bounds", "brick_breaker/paddle.py"],
        ["Brick state and destruction", "brick_breaker/brick.py"],
        ["Collision detection and response", "brick_breaker/collision.py"],
        ["Score and win/loss rules", "brick_breaker/score.py"],
        ["Protocol-level smoke and core rule test", "tests/test_main.py"],
    ],
)


TESTABLE_CORE_BOUNDARY = ActionNode(
    key="Testable Core Boundary",
    expected_type=dict,
    instruction=(
        TESTABLE_CORE_BOUNDARY_INSTRUCTION
        + " Use exact paths from Canonical File References only."
    ),
    example=GENERIC_TESTABLE_CORE_BOUNDARY_EXAMPLE,
)


CPP_INTERFACE_PLAN = ActionNode(
    key="C++ Interface Plan",
    expected_type=Optional[dict],
    instruction=CPP_INTERFACE_PLAN_INSTRUCTION,
    example={
        "uses_header_files": True,
        "header_files": [
            "include/Game.h",
            "include/Ball.h",
            "include/Paddle.h",
            "include/Brick.h",
            "include/Collision.h",
            "include/Score.h",
        ],
        "source_files": [
            "src/Game.cpp",
            "src/Ball.cpp",
            "src/Paddle.cpp",
            "src/Brick.cpp",
            "src/Collision.cpp",
            "src/Score.cpp",
        ],
        "test_includes_must_reference_declared_headers_only": True,
    },
)


TEST_INCLUDE_AUDIT = ActionNode(
    key="Test Include Audit",
    expected_type=Optional[dict],
    instruction=TEST_INCLUDE_AUDIT_INSTRUCTION,
    example={
        "declared_test_includes": [
            "include/Game.h",
            "include/Ball.h",
            "include/Paddle.h",
            "include/Brick.h",
        ],
        "undeclared_test_includes": [],
        "all_test_includes_declared": True,
    },
)


PROTOCOL_COMPLIANCE_CHECK = ActionNode(
    key="Protocol Compliance Check",
    expected_type=dict,
    instruction=PROTOCOL_COMPLIANCE_CHECK_INSTRUCTION,
    example={
        "build_file_preserved": True,
        "runtime_entry_preserved": True,
        "test_target_preserved": True,
        "required_files_missing": [],
        "required_files_renamed": [],
        "unexpected_additional_test_files": [],
        "noncanonical_file_references": [],
        "canonical_matches_file_list": True,
        "canonical_missing_from_file_list_copy": [],
        "canonical_extra_paths": [],
        "protocol_violations": [],
    },
)


PROTOCOL_PRESERVATION = ActionNode(
    key="Protocol Preservation Notes",
    expected_type=str,
    instruction=PROTOCOL_PRESERVATION_INSTRUCTION,
    example=(
        "Build file: requirements.txt. Runtime entry: Main.py. "
        "Test target: tests/test_main.py. Test command: pytest. "
        "Exactly one protocol-level test file is used."
    ),
)


ANYTHING_UNCLEAR = ActionNode(
    key="Anything UNCLEAR",
    expected_type=str,
    instruction="Mention unclear aspects if any; otherwise leave empty.",
    example="",
)


NODES = [
    IMPLEMENTATION_APPROACH,
    DOMAIN_DECOMPOSITION,
    FILE_LIST,
    CANONICAL_FILE_REFERENCES,
    DATA_STRUCTURES_AND_INTERFACES,
    PROGRAM_CALL_FLOW,
    DOMAIN_MAPPING,
    TESTABLE_CORE_BOUNDARY,
    CPP_INTERFACE_PLAN,
    TEST_INCLUDE_AUDIT,
    PROTOCOL_COMPLIANCE_CHECK,
    PROTOCOL_PRESERVATION,
    ANYTHING_UNCLEAR,
]


REFINED_NODES = [
    REFINED_IMPLEMENTATION_APPROACH,
    REFINED_FILE_LIST,
    REFINED_DATA_STRUCTURES_AND_INTERFACES,
    REFINED_PROGRAM_CALL_FLOW,
    ANYTHING_UNCLEAR,
]


DESIGN_API_NODE = ActionNode.from_children("DesignAPI", NODES)
REFINED_DESIGN_NODE = ActionNode.from_children("RefinedDesignAPI", REFINED_NODES)