# tests/rulesTest/test_condition_parentheses.py
from pyCodeObfuscator.core.parser import parse_code, code_from_module
from pyCodeObfuscator.core.rule_base import RuleDirection
from pyCodeObfuscator.rules.AL.expression.condition_parentheses import (
    ConditionParenthesesRule,
)


def _apply(src: str, direction: RuleDirection) -> str:
    module = parse_code(src)
    module = module.visit(ConditionParenthesesRule(direction=direction))
    return code_from_module(module)


# ---- if ----
def test_has_parens_to_no_parens_to_variant():
    original = """
def f(userid):
    if (userid == 0):
        return 0
"""
    expected = """
def f(userid):
    if userid == 0:
        return 0
"""
    # 统一去掉外层括号
    assert _apply(original, RuleDirection.to_variant("no_parens")).strip() == expected.strip()


def test_no_parens_to_has_parens_to_variant():
    original = """
def f(userid):
    if userid == 0:
        return 0
"""
    expected = """
def f(userid):
    if (userid == 0):
        return 0
"""
    # 统一加上一层括号
    assert _apply(original, RuleDirection.to_variant("parens")).strip() == expected.strip()


def test_auto_mixed_conditions():
    src = """
def f(userid, flag):
    if (userid == 0):
        return 0

    if flag and userid > 10:
        return 1
"""
    # AUTO 下：
    # - 第一个 if: HAS_PARENS -> 去括号
    # - 第二个 if: NO_PARENS  -> 加括号
    expected = """
def f(userid, flag):
    if userid == 0:
        return 0

    if (flag and userid > 10):
        return 1
"""
    assert _apply(src, RuleDirection.AUTO).strip() == expected.strip()


# ---- while ----

def test_while_has_parens_to_no_parens_to_variant():
    original = """
def f(userid):
    while (userid == 0):
        return 0
"""
    expected = """
def f(userid):
    while userid == 0:
        return 0
"""
    assert _apply(original, RuleDirection.to_variant("no_parens")).strip() == expected.strip()


def test_while_no_parens_to_has_parens_to_variant():
    original = """
def f(userid):
    while userid == 0:
        return 0
"""
    expected = """
def f(userid):
    while (userid == 0):
        return 0
"""
    assert _apply(original, RuleDirection.to_variant("parens")).strip() == expected.strip()


def test_auto_mixed_while_conditions():
    src = """
def f(userid, flag):
    while (userid == 0):
        userid += 1

    while flag and userid > 10:
        userid -= 1
"""
    # AUTO 下：
    # - 第一个 while: HAS_PARENS -> 去括号
    # - 第二个 while: NO_PARENS  -> 加括号
    expected = """
def f(userid, flag):
    while userid == 0:
        userid += 1

    while (flag and userid > 10):
        userid -= 1
"""
    assert _apply(src, RuleDirection.AUTO).strip() == expected.strip()


# ---- assert ----

def test_assert_has_parens_to_no_parens_to_variant():
    original = """
def f(userid):
    assert (userid == 0)
"""
    expected = """
def f(userid):
    assert userid == 0
"""
    assert _apply(original, RuleDirection.to_variant("no_parens")).strip() == expected.strip()


def test_assert_no_parens_to_has_parens_to_variant():
    original = """
def f(userid):
    assert userid == 0
"""
    expected = """
def f(userid):
    assert (userid == 0)
"""
    assert _apply(original, RuleDirection.to_variant("parens")).strip() == expected.strip()


def test_auto_mixed_assert_conditions():
    src = """
def f(userid, flag):
    assert (userid == 0)

    assert flag and userid > 10
"""
    # AUTO 下：
    # - 第一个 assert: HAS_PARENS -> 去括号
    # - 第二个 assert: NO_PARENS  -> 加括号
    expected = """
def f(userid, flag):
    assert userid == 0

    assert (flag and userid > 10)
"""
    assert _apply(src, RuleDirection.AUTO).strip() == expected.strip()


# ---- 三元表达式 ----

def test_ifexp_has_parens_to_no_parens_to_variant():
    original = """
def f(userid):
    return 0 if (userid == 0) else 1
"""
    expected = """
def f(userid):
    return 0 if userid == 0 else 1
"""
    assert _apply(original, RuleDirection.to_variant("no_parens")).strip() == expected.strip()


def test_ifexp_no_parens_to_has_parens_to_variant():
    original = """
def f(userid):
    return 0 if userid == 0 else 1
"""
    expected = """
def f(userid):
    return 0 if (userid == 0) else 1
"""
    assert _apply(original, RuleDirection.to_variant("parens")).strip() == expected.strip()


def test_auto_mixed_ifexp_conditions():
    src = """
def f(userid, flag):
    v1 = 0 if (userid == 0) else 1
    v2 = 0 if flag and userid > 10 else 1
    return v1, v2
"""
    # AUTO 下：
    # - v1 条件: HAS_PARENS -> 去括号
    # - v2 条件: NO_PARENS  -> 加括号
    expected = """
def f(userid, flag):
    v1 = 0 if userid == 0 else 1
    v2 = 0 if (flag and userid > 10) else 1
    return v1, v2
"""
    assert _apply(src, RuleDirection.AUTO).strip() == expected.strip()


# ---- 推导式中的 if ----

def test_comprehension_if_has_parens_to_no_parens_to_variant():
    original = """
def f(xs):
    return [x for x in xs if (x > 0)]
"""
    expected = """
def f(xs):
    return [x for x in xs if x > 0]
"""
    assert _apply(original, RuleDirection.to_variant("no_parens")).strip() == expected.strip()


def test_comprehension_if_no_parens_to_has_parens_to_variant():
    original = """
def f(xs):
    return [x for x in xs if x > 0]
"""
    expected = """
def f(xs):
    return [x for x in xs if (x > 0)]
"""
    assert _apply(original, RuleDirection.to_variant("parens")).strip() == expected.strip()


def test_auto_mixed_comprehension_if_conditions():
    src = """
def f(xs, ys):
    a = [x for x in xs if (x > 0)]
    b = [y for y in ys if y > 0]
    return a, b
"""
    # AUTO 下：
    # - a 的 if 条件: HAS_PARENS -> 去括号
    # - b 的 if 条件: NO_PARENS  -> 加括号
    expected = """
def f(xs, ys):
    a = [x for x in xs if x > 0]
    b = [y for y in ys if (y > 0)]
    return a, b
"""
    assert _apply(src, RuleDirection.AUTO).strip() == expected.strip()
