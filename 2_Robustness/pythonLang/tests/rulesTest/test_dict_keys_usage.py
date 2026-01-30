# tests/rulesTest/test_dict_keys_usage.py
from pyCodeObfuscator.core.parser import parse_code, code_from_module
from pyCodeObfuscator.core.rule_base import RuleDirection
from pyCodeObfuscator.rules.AL.expression.dict_keys_usage import DictKeysUsageRule


def _apply(src: str, direction: RuleDirection) -> str:
    module = parse_code(src)
    module = module.visit(DictKeysUsageRule(direction=direction))
    return code_from_module(module)


def test_direct_to_keys_to_variant():
    original = """
def f(d):
    if "Alice" in d:
        return 1
"""
    expected = """
def f(d):
    if "Alice" in d.keys():
        return 1
"""
    # 统一转为 d.keys() 形式
    assert _apply(original, RuleDirection.to_variant("keys")).strip() == expected.strip()


def test_keys_to_direct_to_variant():
    original = """
def f(d):
    if "Alice" in d.keys():
        return 1
"""
    expected = """
def f(d):
    if "Alice" in d:
        return 1
"""
    # 统一转为裸 in d 形式
    assert _apply(original, RuleDirection.to_variant("direct")).strip() == expected.strip()


def test_auto_mixed_direct_and_keys():
    src = """
def f(d):
    if "Alice" in d:
        a = 1
    if "Bob" in d.keys():
        b = 2
    return a + b
"""
    # AUTO：
    #   第一处：DIRECT_IN  -> KEYS_API
    #   第二处：KEYS_API   -> DIRECT_IN
    expected = """
def f(d):
    if "Alice" in d.keys():
        a = 1
    if "Bob" in d:
        b = 2
    return a + b
"""
    assert _apply(src, RuleDirection.AUTO).strip() == expected.strip()
