#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/12/14 11:40
@Author  : alexanderwu
@File    : write_prd_an.py
"""

from typing import List

from metagpt.actions.action_node import ActionNode
from .protocol_shared_an import (
    DOMAIN_EXPECTATIONS_INSTRUCTION,
    DOMAIN_REASONING_INSTRUCTION,
    GENERAL_TESTING_CONSTRAINTS_INSTRUCTION,
    GENERIC_DOMAIN_EXPECTATIONS_EXAMPLE,
    GENERIC_DOMAIN_REASONING_EXAMPLE,
    INTERFACE_PROTOCOL_INSTRUCTION,
    LANGUAGE_CONVENTION_REQUIREMENTS_INSTRUCTION,
)


LANGUAGE = ActionNode(
    key="Language",
    expected_type=str,
    instruction="Provide the language used in the project, typically matching the user's requirement language.",
    example="en_us",
)


PROGRAMMING_LANGUAGE = ActionNode(
    key="Programming Language",
    expected_type=str,
    instruction=(
        "Specify the programming language requested by the user. "
        "Typical values include Python, Java, C++, JavaScript, Go, Rust, etc. "
        "This field must align with the intended build/test ecosystem."
    ),
    example="Python",
)


ORIGINAL_REQUIREMENTS = ActionNode(
    key="Original Requirements",
    expected_type=str,
    instruction="Place the original user's requirements here.",
    example="Create a Brick Breaker game",
)


REFINED_REQUIREMENTS = ActionNode(
    key="Refined Requirements",
    expected_type=str,
    instruction="Place the new user's refined or incremental requirements here.",
    example="Add scoring and multiple levels to the Brick Breaker game.",
)


PROJECT_NAME = ActionNode(
    key="Project Name",
    expected_type=str,
    instruction=(
        'According to "Original Requirements", name the project using snake_case style, '
        "such as brick_breaker_game, game_2048, simple_crm, or calculator_app."
    ),
    example="brick_breaker_game",
)


INTERFACE_PROTOCOL = ActionNode(
    key="Interface Protocol",
    expected_type=str,
    instruction=INTERFACE_PROTOCOL_INSTRUCTION,
    example=(
        "Python: build_file=requirements.txt, runtime_entry=Main.py, test_target=tests/test_main.py, test_command=pytest."
        "Java: build_file=pom.xml, runtime_entry=src/main/java/Main.java, test_target=src/test/java/MainTest.java, test_command=mvn test."
        "C++: build_file=CMakeLists.txt, runtime_entry=src/Main.cpp, test_target=tests/test_main.cpp, test_command=ctest."
    ),
)


PROTOCOL_CONTRACT = ActionNode(
    key="Protocol Contract",
    expected_type=dict,
    instruction=(
        "Output the exact protocol contract for the selected programming language. "
        "Use supported protocol paths only. "
        "Do not invent, rename, move, replace, generalize, or reinterpret protocol files. "
        "Fields: build_file, runtime_entry, test_target, test_command, required_files_exact."
    ),
    example={
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
)


TESTING_CONSTRAINTS = ActionNode(
    key="Testing Constraints",
    expected_type=List[str],
    instruction=GENERAL_TESTING_CONSTRAINTS_INSTRUCTION,
    example=[
        "Exactly one protocol-level test file",
        "No manual interaction",
        "Minimal core-rule coverage",
    ],
)


LANGUAGE_CONVENTION_REQUIREMENTS = ActionNode(
    key="Language Convention Requirements",
    expected_type=List[str],
    instruction=LANGUAGE_CONVENTION_REQUIREMENTS_INSTRUCTION,
    example=[
        "Python: keep Main.py thin and use a package for extra modules.",
        "Java: use Maven layout.",
        "C++: use include/ and src/ when multiple translation units exist.",
    ],
)


DOMAIN_REASONING = ActionNode(
    key="Domain Reasoning",
    expected_type=List[str],
    instruction=DOMAIN_REASONING_INSTRUCTION,
    example=GENERIC_DOMAIN_REASONING_EXAMPLE,
)


DOMAIN_EXPECTATIONS = ActionNode(
    key="Domain Expectations",
    expected_type=List[str],
    instruction=DOMAIN_EXPECTATIONS_INSTRUCTION,
    example=GENERIC_DOMAIN_EXPECTATIONS_EXAMPLE,
)


PRODUCT_GOALS = ActionNode(
    key="Product Goals",
    expected_type=List[str],
    instruction="Provide up to three clear, orthogonal product goals.",
    example=[
        "Deliver correct core functionality",
        "Keep the project easy to understand and maintain",
        "Provide a reliable automated testing path",
    ],
)


REFINED_PRODUCT_GOALS = ActionNode(
    key="Refined Product Goals",
    expected_type=List[str],
    instruction=(
        "Update and expand the original product goals to reflect evolving needs due to incremental development."
    ),
    example=[
        "Enhance usability through new features",
        "Improve maintainability while preserving simple testing",
        "Reduce coupling between runtime/UI and core logic",
    ],
)


USER_STORIES = ActionNode(
    key="User Stories",
    expected_type=List[str],
    instruction="Provide 3 to 5 scenario-based user stories derived from the project requirements.",
    example=[
        "As a user, I want to control the paddle.",
        "As a user, I want bricks to disappear when hit.",
        "As a user, I want to see score updates.",
    ],
)


REFINED_USER_STORIES = ActionNode(
    key="Refined User Stories",
    expected_type=List[str],
    instruction="Update scenario-based user stories to reflect incremental features and improvements.",
    example=[
        "As a user, I want clearer feedback after losing.",
        "As a user, I want new features without breaking existing gameplay.",
    ],
)


COMPETITIVE_ANALYSIS = ActionNode(
    key="Competitive Analysis",
    expected_type=List[str],
    instruction="Provide 3 to 5 competitive or comparable products, tools, or implementations.",
    example=[
        "Classic Breakout: simple mechanics and recognizable gameplay",
        "Arkanoid: richer levels and power-ups",
        "Minimal browser clones: easy to understand but often weakly structured",
    ],
)


COMPETITIVE_QUADRANT_CHART = ActionNode(
    key="Competitive Quadrant Chart",
    expected_type=str,
    instruction="Use mermaid quadrantChart syntax. Keep it concise.",
    example="""quadrantChart
    title "Competitive positioning"
    x-axis "Low Capability" --> "High Capability"
    y-axis "Low Usability" --> "High Usability"
    "Classic Breakout": [0.5, 0.7]
    "Arkanoid": [0.8, 0.6]
    "Our Target Product": [0.6, 0.7]""",
)


REQUIREMENT_ANALYSIS = ActionNode(
    key="Requirement Analysis",
    expected_type=str,
    instruction=(
        "Provide a concise requirement analysis covering functionality, protocol preservation, "
        "testability, and architecture implications."
    ),
    example="The project needs a playable game with separated core logic and a minimal automated test path.",
)


REFINED_REQUIREMENT_ANALYSIS = ActionNode(
    key="Refined Requirement Analysis",
    expected_type=List[str],
    instruction="Review and refine requirement analysis for incremental development.",
    example=[
        "Add new behavior without changing protocol files.",
        "Keep core logic testable without GUI interaction.",
    ],
)


REQUIREMENT_POOL = ActionNode(
    key="Requirement Pool",
    expected_type=List[List[str]],
    instruction="List the top 5 requirements with priority P0, P1, or P2.",
    example=[
        ["P0", "Preserve protocol-required files exactly"],
        ["P0", "Implement core game mechanics"],
        ["P1", "Provide a minimal automated test path"],
    ],
)


REFINED_REQUIREMENT_POOL = ActionNode(
    key="Refined Requirement Pool",
    expected_type=List[List[str]],
    instruction="List top refined requirements with priority P0, P1, or P2.",
    example=[
        ["P0", "Preserve existing protocol files"],
        ["P1", "Add the requested feature"],
    ],
)


UI_DESIGN_DRAFT = ActionNode(
    key="UI / UX / Interaction Design draft",
    expected_type=str,
    instruction=(
        "Describe UI, UX, or interaction design if relevant. "
        "For GUI/game projects, mention that tests should avoid real rendering or manual input."
    ),
    example="A simple 2D game area with paddle, ball, bricks, and score display.",
)


ANYTHING_UNCLEAR = ActionNode(
    key="Anything UNCLEAR",
    expected_type=str,
    instruction="Mention unclear aspects if any; otherwise leave empty.",
    example="",
)


ISSUE_TYPE = ActionNode(
    key="issue_type",
    expected_type=str,
    instruction="Answer BUG/REQUIREMENT. If it is a bugfix, answer BUG, otherwise REQUIREMENT.",
    example="REQUIREMENT",
)


IS_RELATIVE = ActionNode(
    key="is_relative",
    expected_type=str,
    instruction="Answer YES/NO. If the requirement is related to the old PRD, answer YES, otherwise NO.",
    example="YES",
)


REASON = ActionNode(
    key="reason",
    expected_type=str,
    instruction="Explain the reasoning process from question to answer.",
    example="The request extends the existing project requirements.",
)


NODES = [
    LANGUAGE,
    PROGRAMMING_LANGUAGE,
    ORIGINAL_REQUIREMENTS,
    PROJECT_NAME,
    INTERFACE_PROTOCOL,
    PROTOCOL_CONTRACT,
    TESTING_CONSTRAINTS,
    LANGUAGE_CONVENTION_REQUIREMENTS,
    DOMAIN_REASONING,
    DOMAIN_EXPECTATIONS,
    PRODUCT_GOALS,
    USER_STORIES,
    COMPETITIVE_ANALYSIS,
    COMPETITIVE_QUADRANT_CHART,
    REQUIREMENT_ANALYSIS,
    REQUIREMENT_POOL,
    UI_DESIGN_DRAFT,
    ANYTHING_UNCLEAR,
]


REFINED_NODES = [
    LANGUAGE,
    PROGRAMMING_LANGUAGE,
    REFINED_REQUIREMENTS,
    PROJECT_NAME,
    REFINED_PRODUCT_GOALS,
    REFINED_USER_STORIES,
    COMPETITIVE_ANALYSIS,
    COMPETITIVE_QUADRANT_CHART,
    REFINED_REQUIREMENT_ANALYSIS,
    REFINED_REQUIREMENT_POOL,
    UI_DESIGN_DRAFT,
    ANYTHING_UNCLEAR,
]


WRITE_PRD_NODE = ActionNode.from_children("WritePRD", NODES)
REFINED_PRD_NODE = ActionNode.from_children("RefinedPRD", REFINED_NODES)
WP_ISSUE_TYPE_NODE = ActionNode.from_children("WP_ISSUE_TYPE", [ISSUE_TYPE, REASON])
WP_IS_RELATIVE_NODE = ActionNode.from_children("WP_IS_RELATIVE", [IS_RELATIVE, REASON])