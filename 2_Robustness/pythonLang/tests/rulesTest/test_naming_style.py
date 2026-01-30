# tests/rulesTest/test_naming_style.py
from pyCodeObfuscator.core.parser import parse_code, code_from_module
from pyCodeObfuscator.core.rule_base import RuleDirection
from pyCodeObfuscator.rules.NL.naming_style import NamingStyleRule


def _apply(src: str, direction: RuleDirection) -> str:
    module = parse_code(src)
    module = module.visit(NamingStyleRule(direction=direction))
    return code_from_module(module)


def test_camel_to_snake_to_variant():
    src = """
def add(UserAddNum):
    return 1 + UserAddNum
"""
    expected = """
def add(user_add_num):
    return 1 + user_add_num
"""
    # 统一转为 snake_case
    assert _apply(src, RuleDirection.to_variant("snake")).strip() == expected.strip()


def test_snake_to_camel_to_variant():
    src = """
def add(user_add_num):
    return 1 + user_add_num
"""
    expected = """
def add(UserAddNum):
    return 1 + UserAddNum
"""
    # 统一转为 CamelCase
    assert _apply(src, RuleDirection.to_variant("camel")).strip() == expected.strip()


def test_auto_mixed_three_styles():
    src = """
def f(UserAddNum, user_add_num, user_Add_Num):
    x = UserAddNum + user_add_num + user_Add_Num
    return x
"""
    # AUTO 轮转规则：
    #   CAMEL(UserAddNum)      -> SNAKE(user_add_num)
    #   SNAKE(user_add_num)    -> PASCAL_UNDERSCORE(user_Add_Num)
    #   PASCAL(user_Add_Num)   -> CAMEL(UserAddNum)
    expected = """
def f(user_add_num, user_Add_Num, UserAddNum):
    x = user_add_num + user_Add_Num + UserAddNum
    return x
"""
    assert _apply(src, RuleDirection.AUTO).strip() == expected.strip()
