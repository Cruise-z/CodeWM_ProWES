# tests/rulesTest/test_op_opequal_usage.py
from __future__ import annotations

from pyCodeObfuscator.core.parser import parse_code, code_from_module
from pyCodeObfuscator.core.rule_base import RuleDirection
from pyCodeObfuscator.rules.AL.expression.op_opequal_usage import (
    OpOrOpEqualUsageRule,
)


def _apply(src: str, direction: RuleDirection) -> str:
    module = parse_code(src)
    module = module.visit(OpOrOpEqualUsageRule(direction=direction))
    return code_from_module(module)


def test_to_variant_opequal_basic():
    src = """
def f():
    t = t + score
    u = u - 1
    x = x * 2
    y = y / 3
"""
    expected = """
def f():
    t += score
    u -= 1
    x *= 2
    y /= 3
"""
    out = _apply(src, RuleDirection.to_variant("opequal"))
    assert out.strip() == expected.strip()


def test_to_variant_op_assign_basic():
    src = """
def f():
    t += score
    u -= 1
    x *= 2
    y /= 3
"""
    expected = """
def f():
    t = t + score
    u = u - 1
    x = x * 2
    y = y / 3
"""
    out = _apply(src, RuleDirection.to_variant("op_assign"))
    assert out.strip() == expected.strip()


def test_auto_flip_between_forms_mixed():
    src = """
def f():
    a = a + 1
    b -= 2
    c = c * 3
    d /= 4
"""
    # AUTO：遇到哪种就翻转到另一种
    expected = """
def f():
    a += 1
    b = b - 2
    c *= 3
    d = d / 4
"""
    out = _apply(src, RuleDirection.AUTO)
    assert out.strip() == expected.strip()
