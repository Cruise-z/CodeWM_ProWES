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
    Apply all rules to the same Module in sequence.

    Parameters:
      - module     : a parsed libcst.Module
      - rule_types : the set of rule types to apply (the classes themselves)
      - direction  : the global direction (RuleDirection), for example:
                        - RuleDirection.AUTO
                        - RuleDirection.to_variant("camel")
                        - RuleDirection.to_variant("snake")
                        - RuleDirection.to_variant("percent")
                        - ...

    Each rule receives the same direction in __init__,
    then interprets it according to its own multi-variant semantics.
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
    Apply a group of rules to a source string and return the rewritten source.
    """
    module = parse_code(source)
    module = apply_rules_to_module(module, rule_types, direction)
    return code_from_module(module)
