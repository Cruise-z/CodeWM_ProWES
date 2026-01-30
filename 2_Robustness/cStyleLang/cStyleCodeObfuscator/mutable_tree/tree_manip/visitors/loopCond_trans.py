#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
loopCond_trans.py

A combination visitor that trans loop condition(true&1) in C-style language ASTs.
- loop_condition.py

Author: Cruise-z <cruise.zrz@gmail.com>
Affiliation: IIE CAS
Date: 2025-11-07
"""
import random
from typing import Optional

from .visitor import TransformingVisitor
from ...nodes import Node
from ...nodes import node_factory
from ...nodes import WhileStatement, ForStatement, Literal


class LoopCondTransVisitor(TransformingVisitor):
    """
    Randomly toggle loop conditions among { true, 1, None }:

    - For `while` loops: condition must be an expression; we only toggle between `true` <-> `1`.
      (Setting `None` is invalid for while, so it's excluded automatically.)
    - For `for` loops: condition may be `true`, `1`, or `None` (omitted). When we see one,
      we randomly convert it to one of the other two.

    Behavior mirrors the original LoopLiteralOneVisitor / LoopLiteralTrueVisitor:
    - Children are visited first.
    - Only acts when the condition is exactly a literal "true"/"1" or (for `for`) None.
    """

    def __init__(self, seed: Optional[int] = None):
        super().__init__()
        self._rng = random.Random(seed)

    # ---- helpers ----

    @staticmethod
    def _lit_is_true(n: Node) -> bool:
        return isinstance(n, Literal) and getattr(n, "value", None) == "true"

    @staticmethod
    def _lit_is_one(n: Node) -> bool:
        return isinstance(n, Literal) and getattr(n, "value", None) == "1"

    def _choose_target_for_while(self, cur: str) -> Optional[str]:
        """
        cur in {"true", "1"}; candidates are the other valid while targets (cannot be None).
        Returns one of {"true","1"} different from cur.
        """
        if cur == "true":
            return "1"
        if cur == "1":
            return "true"
        return None  # not handled

    def _choose_target_for_for(self, cur: Optional[str]) -> Optional[Optional[str]]:
        """
        cur in {None, "true", "1"}; candidates are the other two of the trio.
        Returns one of {None,"true","1"} different from cur.
        """
        all_vals = [None, "true", "1"]
        candidates = [v for v in all_vals if v != cur]
        if not candidates:
            return None
        return self._rng.choice(candidates)

    # ---- visitors ----

    def visit_WhileStatement(
        self,
        node: WhileStatement,
        parent: Optional[Node] = None,
        parent_attr: Optional[str] = None,
    ):
        # visit children first (consistent with original visitors)
        self.generic_visit(node, parent, parent_attr)

        cond = node.condition
        # Only handle literal true/1 for while
        if self._lit_is_true(cond):
            target = self._choose_target_for_while("true")
        elif self._lit_is_one(cond):
            target = self._choose_target_for_while("1")
        else:
            return False, []

        if target == "true":
            node.condition = node_factory.create_literal("true")
        elif target == "1":
            node.condition = node_factory.create_literal("1")
        else:
            # Shouldn't happen for while (we never choose None)
            return False, []

        return True, [node]

    def visit_ForStatement(
        self,
        node: ForStatement,
        parent: Optional[Node] = None,
        parent_attr: Optional[str] = None,
    ):
        # visit children first
        self.generic_visit(node, parent, parent_attr)

        cond = node.condition
        # Determine current representation among {None, "true", "1"}
        if cond is None:
            cur = None
        elif self._lit_is_true(cond):
            cur = "true"
        elif self._lit_is_one(cond):
            cur = "1"
        else:
            return False, []

        # Randomly pick one of the other two
        target = self._choose_target_for_for(cur)
        if target is cur:  # no-op guard (shouldn't occur)
            return False, []

        if target is None:
            node.condition = None
        elif target == "true":
            node.condition = node_factory.create_literal("true")
        elif target == "1":
            node.condition = node_factory.create_literal("1")
        else:
            return False, []

        return True, [node]
