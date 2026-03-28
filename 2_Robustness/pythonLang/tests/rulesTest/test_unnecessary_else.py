# tests/rulesTest/test_unnecessary_else.py
from pyCodeObfuscator.core.parser import parse_code, code_from_module
from pyCodeObfuscator.rules.AL.block.unnecessary_else import (
    RemoveUnnecessaryElseRule,
)
from pyCodeObfuscator.core.rule_base import RuleDirection


def _apply(src: str, direction: RuleDirection) -> str:
    module = parse_code(src)
    module = module.visit(RemoveUnnecessaryElseRule(direction=direction))
    return code_from_module(module)


def test_original_to_transformed_no_else():
    original = """
def f(a=None):
    if a is None:
        return 1
    else:
        x = 2
        print(x)
"""
    expected = """
def f(a=None):
    if a is None:
        return 1
    x = 2
    print(x)
"""
    # Normalize to the "no else" form
    assert _apply(original, RuleDirection.to_variant("no_else")).strip() == expected.strip()


def test_transformed_to_original_with_else():
    transformed = """
def f(a=None):
    if a is None:
        return 1
    x = 2
    print(x)
"""
    expected = """
def f(a=None):
    if a is None:
        return 1
    else:
        x = 2
        print(x)
"""
    # Normalize to the "with else" form
    assert _apply(transformed, RuleDirection.to_variant("with_else")).strip() == expected.strip()


def test_auto_mixed_original_and_transformed():
    # f uses the original form (with else)
    # g uses the transformed form (without else)
    src = """
def f(a=None):
    if a is None:
        print("zzz")
        return 1
    else:
        x = 2
        print(x)
        for i in range(3):
            print(i)
    z = 0

def g(a=None):
    if a is None:
        print("zzz")
        return 1
    x = 2
    print(x)
"""

    # Expected:
    # - f: original -> transformed (remove else and sink the else body downward)
    # - g: transformed -> original (pull the following statements into else)
    expected = """
def f(a=None):
    if a is None:
        print("zzz")
        return 1
    x = 2
    print(x)
    for i in range(3):
        print(i)
    z = 0

def g(a=None):
    if a is None:
        print("zzz")
        return 1
    else:
        x = 2
        print(x)
"""

    assert _apply(src, RuleDirection.AUTO).strip() == expected.strip()
