# tests/rulesTest/test_for_to_list_comprehension.py
from pyCodeObfuscator.core.parser import parse_code, code_from_module
from pyCodeObfuscator.core.rule_base import RuleDirection
from pyCodeObfuscator.rules.AL.block.for_to_list_comprehension import (
    ForToListComprehensionRule,
)


def _apply(src: str, direction: RuleDirection) -> str:
    module = parse_code(src)
    module = module.visit(ForToListComprehensionRule(direction=direction))
    return code_from_module(module)


def test_loop_based_to_comprehension_to_variant():
    original = """
def f():
    cubes = []
    for i in range(20):
        cubes.append(i**3)
    return cubes
"""
    expected = """
def f():
    cubes = [i**3 for i in range(20)]
    return cubes
"""
    # 统一转为列表推导（comprehension）
    assert _apply(original, RuleDirection.to_variant("comprehension")).strip() == expected.strip()


def test_comprehension_to_loop_based_to_variant():
    original = """
def f():
    cubes = [i**3 for i in range(20)]
    return cubes
"""
    expected = """
def f():
    cubes = []
    for i in range(20):
        cubes.append(i**3)
    return cubes
"""
    # 统一转为 loop-based 形态
    assert _apply(original, RuleDirection.to_variant("loop")).strip() == expected.strip()


def test_auto_mixed_loop_and_comprehension():
    src = """
def f():
    cubes = []
    for i in range(20):
        cubes.append(i**3)

    squares = [j**2 for j in range(10)]
    return cubes, squares
"""
    # AUTO 下：
    # - cubes 部分：LOOP_BASED -> COMPREHENSION_BASED
    # - squares 部分：COMPREHENSION_BASED -> LOOP_BASED
    expected = """
def f():
    cubes = [i**3 for i in range(20)]

    squares = []
    for j in range(10):
        squares.append(j**2)
    return cubes, squares
"""
    assert _apply(src, RuleDirection.AUTO).strip() == expected.strip()
