#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
varNameStyle_trans.py

A combination visitor that trans var name style in C-style language ASTs.
- var_naming_style.py

Author: Cruise-z <cruise.zrz@gmail.com>
Affiliation: IIE CAS
Date: 2025-11-08
"""
import random
from typing import Optional

from .visitor import TransformingVisitor
from .var_name_utils import (
    is_underscore_case,
    sanitize_name_for_styling,
    remove_preceding_underscores,
)
from ...nodes import Node, NodeType, node_factory
from ...nodes import VariableDeclarator, Identifier, FunctionDeclarator
import inflection


class VarNamingVisitor(TransformingVisitor):
    """
    Reuse the base behaviors from your existing file:
    - keep a name mapping so all Identifier usages are consistently renamed
    - don't rename member-access fields or callees
    - only dive into parameter list when visiting a FunctionDeclarator that sits in a FUNCTION_HEADER
    """
    def __init__(self):
        super().__init__()
        self.variable_name_mapping = {}

    def visit_FunctionDeclarator(
        self,
        node: FunctionDeclarator,
        parent: Optional[Node] = None,
        parent_attr: Optional[str] = None,
    ):
        if parent.node_type == NodeType.FUNCTION_HEADER:
            self.generic_visit(node.parameters, node, "parameters")
            return False, []
        else:
            return self.generic_visit(node, parent, parent_attr)

    def visit_Identifier(
        self,
        node: Identifier,
        parent: Optional[Node] = None,
        parent_attr: Optional[str] = None,
    ):
        # Do NOT rename field access: obj.<field>
        if parent.node_type == NodeType.FIELD_ACCESS and parent_attr == "field":
            return False, []

        # Do NOT rename call callee: <callee>(...)
        if parent.node_type == NodeType.CALL_EXPR and parent_attr == "callee":
            return False, []

        name = node.name
        new_name = self.variable_name_mapping.get(name, None)
        if new_name is not None:
            return True, [node_factory.create_identifier(new_name)]
        return False, []


class VarNameStyleTransVisitor(VarNamingVisitor):
    """
    Detect a variable's current naming style among {camelCase, PascalCase, snake_case, _underscore_case}
    and convert it to a RANDOM one of the other three styles.

    - The conversion rules mirror your existing ToCamel/ToPascal/ToSnake/ToUnderscore visitors.
    - A per-instance RNG (optional seed) controls randomness for reproducibility.
    - Once a declarator is renamed, all subsequent Identifier occurrences are rewritten via the base mapping.
    """

    STYLES = ("camel", "pascal", "snake", "underscore")

    def __init__(self, seed: Optional[int] = None):
        super().__init__()
        self._rng = random.Random(seed)

    # ---------- style detection (simple, pragmatic heuristics) ----------
    def _detect_style(self, name: str) -> str:
        """
        Order matters to avoid overlap:
          1) leading-underscore style (e.g., _foo, __bar) -> 'underscore'
          2) contains '_' (e.g., snake_case)            -> 'snake'
          3) leading upper (e.g., PascalCase)           -> 'pascal'
          4) fallback                                   -> 'camel'
        """
        if not name:
            return "camel"
        if is_underscore_case(name):
            return "underscore"
        if "_" in name:
            return "snake"
        if name[0].isupper():
            return "pascal"
        return "camel"

    # ---------- per-style converters (reuse logic from provided visitors) ----------
    def _to_camel(self, name: str) -> str:
        if is_underscore_case(name):
            base = remove_preceding_underscores(name)
            new_name = inflection.camelize(base, uppercase_first_letter=False)
        elif all(c.isupper() for c in name if c.isalpha()):
            # keep as-is per your ToCamelCaseVisitor special case
            new_name = name
        else:
            new_name = inflection.camelize(name, uppercase_first_letter=False)
        return sanitize_name_for_styling(new_name)

    def _to_pascal(self, name: str) -> str:
        if is_underscore_case(name):
            base = remove_preceding_underscores(name)
            new_name = inflection.camelize(base, uppercase_first_letter=True)
        else:
            new_name = inflection.camelize(name, uppercase_first_letter=True)
        return sanitize_name_for_styling(new_name)

    def _to_snake(self, name: str) -> str:
        if is_underscore_case(name):
            base = remove_preceding_underscores(name)
            new_name = inflection.underscore(base)
        else:
            new_name = inflection.underscore(name)
        return sanitize_name_for_styling(new_name)

    def _to_underscore(self, name: str) -> str:
        """
        Follow ToUnderscoreCaseVisitor:
        - If already underscore-case, keep unchanged.
        - Else prefix an underscore, then underscore() and sanitize.
        (We map the *original* name to the new result so Identifier lookups stay simple.)
        """
        if is_underscore_case(name):
            return sanitize_name_for_styling(name)
        prefixed = "_" + name
        new_name = inflection.underscore(prefixed)
        return sanitize_name_for_styling(new_name)

    def _convert(self, name: str, target_style: str) -> str:
        if target_style == "camel":
            return self._to_camel(name)
        if target_style == "pascal":
            return self._to_pascal(name)
        if target_style == "snake":
            return self._to_snake(name)
        if target_style == "underscore":
            return self._to_underscore(name)
        # fallback (shouldn't happen)
        return sanitize_name_for_styling(name)

    # ---------- main hook ----------
    def visit_VariableDeclarator(
        self,
        node: VariableDeclarator,
        parent: Optional[Node] = None,
        parent_attr: Optional[str] = None,
    ):
        name = node.decl_id.name

        cur_style = self._detect_style(name)
        # pick a different style
        candidates = [s for s in self.STYLES if s != cur_style]
        target = self._rng.choice(candidates)

        new_name = self._convert(name, target)
        # register mapping (original -> new)
        self.variable_name_mapping[name] = new_name

        # return updated declarator
        decl_id = node_factory.create_identifier(new_name)
        return True, [node_factory.create_variable_declarator(decl_id)]
