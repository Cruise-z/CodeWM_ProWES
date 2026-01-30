# pyCodeObfuscator/core/transformer.py
from __future__ import annotations

from typing import Iterable, Type

import libcst as cst

from .parser import parse_code, code_from_module
from .rule_base import BaseRule, RuleDirection


def apply_rules_to_module(
    module: cst.Module,
    rule_types: Iterable[Type[BaseRule]],
    direction: RuleDirection = RuleDirection.AUTO,
) -> cst.Module:
    """
    按顺序把所有规则应用在同一个 Module 上。

    参数：
      - module     : 已解析的 libcst.Module
      - rule_types : 需要应用的一组规则类型（类本身）
      - direction  : 全局方向（RuleDirection），例如：
                        - RuleDirection.AUTO
                        - RuleDirection.to_variant("camel")
                        - RuleDirection.to_variant("snake")
                        - RuleDirection.to_variant("percent")
                        - ...

    每条规则在 __init__ 中接收同一个 direction，
    然后根据自身定义的多形态语义来解释该 direction。
    """
    for rule_cls in rule_types:
        transformer = rule_cls(direction=direction)
        module = module.visit(transformer)
    return module


def obfuscate_source(
    source: str,
    rule_types: Iterable[Type[BaseRule]],
    direction: RuleDirection = RuleDirection.AUTO,
) -> str:
    """
    对源码字符串应用一组规则，并返回改写后的源码。
    """
    module = parse_code(source)
    module = apply_rules_to_module(module, rule_types, direction)
    return code_from_module(module)
