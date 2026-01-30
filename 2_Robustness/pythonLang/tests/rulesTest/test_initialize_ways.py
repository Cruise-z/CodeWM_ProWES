# tests/rulesTest/test_initialize_ways.py
from __future__ import annotations

from pyCodeObfuscator.core.parser import parse_code, code_from_module
from pyCodeObfuscator.core.rule_base import RuleDirection
from pyCodeObfuscator.rules.AL.block.initialize_ways import InitializeWaysRule


def _apply(src: str, direction: RuleDirection) -> str:
    module = parse_code(src)
    module = module.visit(InitializeWaysRule(direction=direction))
    return code_from_module(module)


def test_to_variant_dict_call():
    src = """
def f():
    d = {}
    d["name"] = "1"
    x = 42
"""
    expected = """
def f():
    d = dict(name = "1")
    x = 42
"""
    out = _apply(src, RuleDirection.to_variant("dict_call"))
    assert out.strip() == expected.strip()


def test_to_variant_empty_subscript():
    src = """
def f():
    d = dict(name="1")
    x = 42
"""
    expected = """
def f():
    d = {}
    d['name'] = "1"
    x = 42
"""
    out = _apply(src, RuleDirection.to_variant("empty_subscript"))
    assert out.strip() == expected.strip()


def test_auto_flip_both_directions():
    src = """
def f():
    d1 = dict(name="1")
    d2 = {}
    d2["name"] = "2"
"""
    expected = """
def f():
    d1 = {}
    d1['name'] = "1"
    d2 = dict(name = "2")
"""
    out = _apply(src, RuleDirection.AUTO)
    assert out.strip() == expected.strip()
