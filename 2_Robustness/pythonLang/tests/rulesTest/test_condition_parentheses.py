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
    # Normalize by removing the outer parentheses
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
    # Normalize by adding one outer layer of parentheses
    assert _apply(original, RuleDirection.to_variant("parens")).strip() == expected.strip()


def test_auto_mixed_conditions():
    src = """
def f(userid, flag):
    if (userid == 0):
        return 0

    if flag and userid > 10:
        return 1
"""
    # Under AUTO:
    # - first if: HAS_PARENS -> remove parentheses
    # - second if: NO_PARENS -> add parentheses
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
    # Under AUTO:
    # - first while: HAS_PARENS -> remove parentheses
    # - second while: NO_PARENS -> add parentheses
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
    # Under AUTO:
    # - first assert: HAS_PARENS -> remove parentheses
    # - second assert: NO_PARENS -> add parentheses
    expected = """
def f(userid, flag):
    assert userid == 0

    assert (flag and userid > 10)
"""
    assert _apply(src, RuleDirection.AUTO).strip() == expected.strip()


# ---- Ternary expressions ----

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
    # Under AUTO:
    # - v1 condition: HAS_PARENS -> remove parentheses
    # - v2 condition: NO_PARENS -> add parentheses
    expected = """
def f(userid, flag):
    v1 = 0 if userid == 0 else 1
    v2 = 0 if (flag and userid > 10) else 1
    return v1, v2
"""
    assert _apply(src, RuleDirection.AUTO).strip() == expected.strip()


# ---- if inside comprehensions ----

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
    # Under AUTO:
    # - a's if condition: HAS_PARENS -> remove parentheses
    # - b's if condition: NO_PARENS -> add parentheses
    expected = """
def f(xs, ys):
    a = [x for x in xs if x > 0]
    b = [y for y in ys if (y > 0)]
    return a, b
"""
    assert _apply(src, RuleDirection.AUTO).strip() == expected.strip()
