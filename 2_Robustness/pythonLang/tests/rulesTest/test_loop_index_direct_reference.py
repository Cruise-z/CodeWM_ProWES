# tests/rulesTest/test_loop_index_direct_reference.py
from pyCodeObfuscator.core.parser import parse_code, code_from_module
from pyCodeObfuscator.core.rule_base import RuleDirection
from pyCodeObfuscator.rules.AL.block.loop_index_direct_reference import (
    LoopIndexDirectReferenceRule,
)


def _apply(src: str, direction: RuleDirection) -> str:
    module = parse_code(src)
    module = module.visit(LoopIndexDirectReferenceRule(direction=direction))
    return code_from_module(module)


def test_index_loop_to_direct_to_variant():
    original = """
def f():
    for i in range(len(currencies)):
        print(currencies[i])
    for j in range(len(users)):
        x = users[j].name
"""

    expected = """
def f():
    for currency in currencies:
        print(currency)
    for user in users:
        x = user.name
"""

    # 统一转为 element-based 形态
    assert _apply(original, RuleDirection.to_variant("element")).strip() == expected.strip()


def test_direct_loop_to_index_to_variant():
    original = """
def f():
    for currency in currencies:
        print(currency)
    for user in users:
        x = user.name
"""

    expected = """
def f():
    for currency_idx in range(len(currencies)):
        print(currencies[currency_idx])
    for user_idx in range(len(users)):
        x = users[user_idx].name
"""

    # 统一转为 index-based 形态
    assert _apply(original, RuleDirection.to_variant("index")).strip() == expected.strip()


def test_auto_mixed_index_and_direct():
    # f 使用 index 形式，g 使用 element 形式
    src = """
def f():
    for i in range(len(currencies)):
        print(currencies[i])

def g():
    for currency in currencies:
        print(currency)
"""

    # AUTO 模式下:
    # - f: index -> element
    # - g: element -> index
    expected = """
def f():
    for currency in currencies:
        print(currency)

def g():
    for currency_idx in range(len(currencies)):
        print(currencies[currency_idx])
"""

    assert _apply(src, RuleDirection.AUTO).strip() == expected.strip()
