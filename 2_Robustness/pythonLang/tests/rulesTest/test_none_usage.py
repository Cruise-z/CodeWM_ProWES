# tests/rulesTest/test_none_usage.py
from pyCodeObfuscator.core.parser import parse_code, code_from_module
from pyCodeObfuscator.core.rule_base import RuleDirection
from pyCodeObfuscator.rules.AL.expression.none_usage import NoneUsageRule


def _apply(src: str, direction: RuleDirection) -> str:
    module = parse_code(src)
    module = module.visit(NoneUsageRule(direction=direction))
    return code_from_module(module)


def test_if_bare_to_is_not_none_to_variant():
    original = """
def f(x):
    if x:
        return 1
"""
    expected = """
def f(x):
    if x is not None:
        return 1
"""
    # 统一转为显式 x is not None
    assert _apply(original, RuleDirection.to_variant("is_not_none")).strip() == expected.strip()


def test_if_is_not_none_to_bare_to_variant():
    original = """
def f(x):
    if x is not None:
        return 1
"""
    expected = """
def f(x):
    if x:
        return 1
"""
    # 统一转为裸 truthy 检查
    assert _apply(original, RuleDirection.to_variant("bare")).strip() == expected.strip()


def test_auto_mixed_if_conditions():
    src = """
def f(x, y):
    if x:
        a = 1
    if y is not None:
        b = 2
    return a + b
"""
    # AUTO 下：
    # - 第一个 if: BARE_TRUTHY -> IS_NOT_NONE
    # - 第二个 if: IS_NOT_NONE -> BARE_TRUTHY
    expected = """
def f(x, y):
    if x is not None:
        a = 1
    if y:
        b = 2
    return a + b
"""
    assert _apply(src, RuleDirection.AUTO).strip() == expected.strip()
