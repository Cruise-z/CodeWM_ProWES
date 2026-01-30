# tests/rulesTest/test_boolean_explicit_true_false.py
from pyCodeObfuscator.core.parser import parse_code, code_from_module
from pyCodeObfuscator.core.rule_base import RuleDirection
from pyCodeObfuscator.rules.AL.expression.boolean_explicit_true_false import (
    BooleanExplicitTrueFalseRule,
)


def _apply(src: str, direction: RuleDirection) -> str:
    module = parse_code(src)
    module = module.visit(BooleanExplicitTrueFalseRule(direction=direction))
    return code_from_module(module)


def test_original_to_transformed_direct():
    original = """
def f(a, b):
    flag = True if (a > 0 and b < 5) else False
    return flag
"""
    expected = """
def f(a, b):
    flag = (a > 0 and b < 5)
    return flag
"""
    # 统一转为“直接布尔表达式”形态
    assert _apply(original, RuleDirection.to_variant("direct")).strip() == expected.strip()


def test_transformed_to_original_explicit():
    original = """
def f(a, b):
    flag = a > 0 and b < 5
    return flag
"""
    expected = """
def f(a, b):
    flag = True if a > 0 and b < 5 else False
    return flag
"""
    # 统一转为“显式 True/False”形态
    assert _apply(original, RuleDirection.to_variant("explicit")).strip() == expected.strip()


def test_auto_mixed_original_and_transformed():
    # 同一个函数里既有 original 形式，也有 transformed 形式
    src = """
def f(a, b):
    flag1 = True if a > 0 else False
    flag2 = b < 0
    return flag1, flag2
"""
    # AUTO 下：
    # - flag1: EXPLICIT_TRUE_FALSE  -> DIRECT_EXPR  => flag1 = a > 0
    # - flag2: DIRECT_EXPR          -> EXPLICIT_TRUE_FALSE  => flag2 = True if b < 0 else False
    expected = """
def f(a, b):
    flag1 = a > 0
    flag2 = True if b < 0 else False
    return flag1, flag2
"""
    assert _apply(src, RuleDirection.AUTO).strip() == expected.strip()
