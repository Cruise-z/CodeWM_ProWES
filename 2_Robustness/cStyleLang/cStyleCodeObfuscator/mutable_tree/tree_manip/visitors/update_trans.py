#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_trans.py

A combination visitor that trans varExp update in C-style language ASTs.
- update_assign.py
- update_binop.py
- update_postfix.py
- update_prefix.py

Author: Cruise-z <cruise.zrz@gmail.com>
Affiliation: IIE CAS
Date: 2025-11-07
"""
import random
from typing import Optional, List

from .visitor import TransformingVisitor
from ...nodes import Node, is_primary_expression
from ...nodes import Literal, BinaryExpression
from ...nodes import AssignmentOps, BinaryOps, UpdateOps
from ...nodes import node_factory
from ...nodes import UpdateExpression, AssignmentExpression
from ...stringifiers import BaseStringifier


class UpdateTransVisitor(TransformingVisitor):
    """
    Unify four increment/decrement forms and randomly convert one to another:

    Forms:
      - prefix update:        ++i / --i
      - postfix update:       i++ / i--
      - compound assignment:  i += 1 / i -= 1
      - binary assignment:    i = i + 1 / i = i - 1   (NOTE: not handling i = 1 + i)

    When encountering any one form, convert it to a random one among the other three.
    """

    # Maps reused from your visitors
    update_op_to_assign_op = {
        UpdateOps.INCREMENT: AssignmentOps.PLUS_EQUAL,
        UpdateOps.DECREMENT: AssignmentOps.MINUS_EQUAL,
    }
    update_op_to_bin_op = {
        UpdateOps.INCREMENT: BinaryOps.PLUS,
        UpdateOps.DECREMENT: BinaryOps.MINUS,
    }
    assign_op_to_bin_op = {
        AssignmentOps.PLUS_EQUAL: BinaryOps.PLUS,
        AssignmentOps.MINUS_EQUAL: BinaryOps.MINUS,
    }
    bin_op_to_assign_op = {
        BinaryOps.PLUS: AssignmentOps.PLUS_EQUAL,
        BinaryOps.MINUS: AssignmentOps.MINUS_EQUAL,
    }
    bin_op_to_update_op = {
        BinaryOps.PLUS: UpdateOps.INCREMENT,
        BinaryOps.MINUS: UpdateOps.DECREMENT,
    }

    def __init__(self, seed: Optional[int] = None):
        super().__init__()
        self._rng = random.Random(seed)

    # ---------- helpers ----------

    @staticmethod
    def _is_literal_one(n: Node) -> bool:
        return isinstance(n, Literal) and getattr(n, "value", None) == "1"

    @staticmethod
    def _same_lvalue(a: Node, b: Node) -> bool:
        # stringifier-based structural equality used in your code
        s = BaseStringifier()
        return s.stringify(a) == s.stringify(b)

    @staticmethod
    def _make_assign_one(lhs: Node, op: AssignmentOps) -> AssignmentExpression:
        return node_factory.create_assignment_expr(lhs, node_factory.create_literal("1"), op)

    @staticmethod
    def _make_bin_assign_one(lhs: Node, binop: BinaryOps) -> AssignmentExpression:
        rhs = node_factory.create_binary_expr(lhs, node_factory.create_literal("1"), binop)
        return node_factory.create_assignment_expr(lhs, rhs, AssignmentOps.EQUAL)

    @staticmethod
    def _make_update(lhs: Node, uop: UpdateOps, prefix: bool) -> UpdateExpression:
        return node_factory.create_update_expr(lhs, uop, prefix)

    # ---------- visitors ----------

    def visit_UpdateExpression(
        self,
        expr: UpdateExpression,
        parent: Optional[Node] = None,
        parent_attr: Optional[str] = None,
    ):
        # transform children first
        self.generic_visit(expr, parent, parent_attr)

        # Only handle primary expressions as operands (matches your original constraints)
        if not is_primary_expression(expr.operand):
            return False, None

        current_kind = "prefix" if expr.prefix else "postfix"
        all_kinds: List[str] = ["prefix", "postfix", "assign", "binop"]
        # choose a target kind different from the current one
        candidates = [k for k in all_kinds if k != current_kind]
        target = self._rng.choice(candidates)

        # derive ops
        uop = expr.op
        aop = self.update_op_to_assign_op[uop]
        bop = self.update_op_to_bin_op[uop]
        lhs = expr.operand

        if target == "assign":
            new_node = self._make_assign_one(lhs, aop)
        elif target == "binop":
            new_node = self._make_bin_assign_one(lhs, bop)
        elif target == "prefix":
            new_node = self._make_update(lhs, uop, True)
        elif target == "postfix":
            new_node = self._make_update(lhs, uop, False)
        else:
            return False, None

        return True, [new_node]

    def visit_AssignmentExpression(
        self,
        expr: AssignmentExpression,
        parent: Optional[Node] = None,
        parent_attr: Optional[str] = None,
    ):
        # transform children first
        self.generic_visit(expr, parent, parent_attr)

        lhs = expr.left

        # Case 1: compound assignment i += 1 / i -= 1
        if expr.op in (AssignmentOps.PLUS_EQUAL, AssignmentOps.MINUS_EQUAL) and self._is_literal_one(expr.right):
            current_kind = "assign"
            aop = expr.op
            bop = self.assign_op_to_bin_op[aop]
            uop = self.bin_op_to_update_op[bop]

        # Case 2: binary assignment i = i + 1 / i = i - 1  (not handling i = 1 + i)
        elif expr.op == AssignmentOps.EQUAL and isinstance(expr.right, BinaryExpression):
            bin_expr = expr.right
            if bin_expr.op not in (BinaryOps.PLUS, BinaryOps.MINUS):
                return False, None
            if not self._same_lvalue(lhs, bin_expr.left):
                return False, None
            if not self._is_literal_one(bin_expr.right):
                return False, None

            current_kind = "binop"
            bop = bin_expr.op
            aop = self.bin_op_to_assign_op[bop]
            uop = self.bin_op_to_update_op[bop]

        else:
            # not a supported form
            return False, None

        # Choose a different representation randomly
        all_kinds: List[str] = ["prefix", "postfix", "assign", "binop"]
        candidates = [k for k in all_kinds if k != current_kind]

        # If lhs is not a primary expression, we cannot legally produce ++lhs/--lhs
        if not is_primary_expression(lhs):
            candidates = [k for k in candidates if k not in ("prefix", "postfix")]
            if not candidates:
                return False, None

        target = self._rng.choice(candidates)

        if target == "assign":
            new_node = self._make_assign_one(lhs, aop)
        elif target == "binop":
            new_node = self._make_bin_assign_one(lhs, bop)
        elif target == "prefix":
            new_node = self._make_update(lhs, uop, True)
        elif target == "postfix":
            new_node = self._make_update(lhs, uop, False)
        else:
            return False, None

        return True, [new_node]
