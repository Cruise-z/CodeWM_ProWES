# tests/rulesTest/test_parameter_default_sorted.py
from __future__ import annotations

from pyCodeObfuscator.core.parser import parse_code, code_from_module
from pyCodeObfuscator.core.rule_base import RuleDirection
from pyCodeObfuscator.rules.AL.expression.parameter_default_sorted import (
    ParameterDefaultSortedRule,
)


def _apply(src: str, direction: RuleDirection) -> str:
    module = parse_code(src)
    module = module.visit(ParameterDefaultSortedRule(direction=direction))
    return code_from_module(module)


def test_to_variant_explicit_reverse_false_basic():
    src = """
def f(arr):
    a = sorted(arr)
    b = sorted(arr, key=lambda x: x[0])
    c = sorted(arr, reverse=True)
"""
    expected = """
def f(arr):
    a = sorted(arr, reverse=False)
    b = sorted(arr, key=lambda x: x[0], reverse=False)
    c = sorted(arr, reverse=True)
"""
    out = _apply(src, RuleDirection.to_variant("explicit_reverse_false"))
    assert out.strip() == expected.strip()


def test_to_variant_no_reverse_basic():
    src = """
def f(arr):
    a = sorted(arr, reverse=False)
    b = sorted(arr, key=lambda x: x[0], reverse=False)
    c = sorted(arr, reverse=True)
"""
    expected = """
def f(arr):
    a = sorted(arr)
    b = sorted(arr, key=lambda x: x[0])
    c = sorted(arr, reverse=True)
"""
    out = _apply(src, RuleDirection.to_variant("no_reverse"))
    assert out.strip() == expected.strip()


def test_auto_flip_both_directions():
    src = """
def f(arr):
    a = sorted(arr)
    b = sorted(arr, reverse=False)
    c = sorted(arr, reverse=True)
"""
    expected = """
def f(arr):
    a = sorted(arr, reverse=False)
    b = sorted(arr)
    c = sorted(arr, reverse=True)
"""
    out = _apply(src, RuleDirection.AUTO)
    assert out.strip() == expected.strip()
