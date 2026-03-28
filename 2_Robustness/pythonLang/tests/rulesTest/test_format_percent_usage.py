# tests/rulesTest/test_format_percent_usage.py
from pyCodeObfuscator.core.parser import parse_code, code_from_module
from pyCodeObfuscator.core.rule_base import RuleDirection
from pyCodeObfuscator.rules.AL.expression.format_percent_usage import (
    FormatPercentUsageRule,
)


def _apply(src: str, direction: RuleDirection) -> str:
    module = parse_code(src)
    module = module.visit(FormatPercentUsageRule(direction=direction))
    return code_from_module(module)


def test_percent_to_format_to_variant():
    original = """
def f(h, w,x, y):
    print("%s,%s,%s,%s" % (h, w,x, y))
"""
    expected = """
def f(h, w,x, y):
    print("{},{},{},{}".format(h, w, x, y))
"""
    # Normalize to the format form
    assert _apply(original, RuleDirection.to_variant("format")).strip() == expected.strip()


def test_format_to_percent_to_variant():
    original = """
def f(h, w):
    print("{},{}".format(h, w))
"""
    expected = """
def f(h, w):
    print("%s,%s" % (h, w))
"""
    # Normalize to the percent form
    assert _apply(original, RuleDirection.to_variant("percent")).strip() == expected.strip()


def test_auto_mixed_percent_and_format():
    src = """
def f(h, w, x, y):
    print("%s,%s" % (h, w))
    print("{},{}".format(x, y))
"""
    # Under AUTO:
    # - first line: PERCENT -> FORMAT
    # - second line: FORMAT -> PERCENT
    expected = """
def f(h, w, x, y):
    print("{},{}".format(h, w))
    print("%s,%s" % (x, y))
"""
    assert _apply(src, RuleDirection.AUTO).strip() == expected.strip()


# ---- Extension: support "{0},{1}".format(...) ----

def test_indexed_format_to_percent_to_variant():
    original = """
def f(h, w):
    print("{0},{1}".format(h, w))
"""
    expected = """
def f(h, w):
    print("%s,%s" % (h, w))
"""
    assert _apply(original, RuleDirection.to_variant("percent")).strip() == expected.strip()


def test_auto_mixed_percent_and_indexed_format():
    src = """
def f(h, w, x, y):
    print("%s,%s" % (h, w))
    print("{0},{1}".format(x, y))
"""
    expected = """
def f(h, w, x, y):
    print("{},{}".format(h, w))
    print("%s,%s" % (x, y))
"""
    assert _apply(src, RuleDirection.AUTO).strip() == expected.strip()
