#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
condition_trans.py

A combination visitor that trans condition statement in C-style language ASTs.
- switch_to_if.py
- ternary_to_if.py

Author: Cruise-z <cruise.zrz@gmail.com>
Affiliation: IIE CAS
Date: 2025-11-07
"""
import copy
from typing import Optional

from .visitor import TransformingVisitor
from ...nodes import Node, node_factory
from ...nodes import BinaryOps, AssignmentOps
from ...nodes import (
    # switch-related
    SwitchStatement,
    SwitchCaseList,
    SwitchCase,
    BlockStatement,
    BreakStatement,
    # ternary-related
    Expression,
    ExpressionStatement,
    AssignmentExpression,
    TernaryExpression,
)


class ConditionTransVisitor(TransformingVisitor):
    """
    Combined conditional transformer:
      1) Switch -> chained if-else (only when each non-default case ends with `break`).
      2) Ternary assignment `x = cond ? a : b;` -> `if (cond) { x = a; } else { x = b; }`.
    """

    # ======== Switch -> If helpers (borrowed from SwitchToIfVisitor) ========

    def _can_transform(self, cases: SwitchCaseList) -> bool:
        """
        All cases must end with a `break` (except the last default case).
        """
        n_cases = len(cases.get_children())
        for i, c in enumerate(cases.get_children()):
            if i == n_cases - 1 and c.case is None:
                # last case is default
                continue

            stmts = c.stmts.get_children()
            if len(stmts) == 0:
                return False

            last_stmt = stmts[-1]
            if isinstance(last_stmt, BlockStatement):
                # assume at most one block in the case
                last_stmt = last_stmt.stmts.get_child_at(-1)

            if not isinstance(last_stmt, BreakStatement):
                return False

        return True

    def _remove_break_stmts(self, cases: SwitchCaseList) -> None:
        """
        Remove trailing `break` from each case (including when wrapped in a single block).
        """
        for c in cases.get_children():
            stmts = c.stmts.get_children()
            if len(stmts) == 0:
                continue

            if isinstance(stmts[-1], BreakStatement):
                stmts.pop()

            elif isinstance(stmts[-1], BlockStatement):
                # assume at most one block in the case
                inner = stmts[-1].stmts.get_children()
                if inner and isinstance(inner[-1], BreakStatement):
                    inner.pop()

    # ======== Ternary -> If helper (borrowed from TernaryToIfVisitor) ========

    def _wrap_assignment_block(self, lhs: Expression, rhs: Expression) -> BlockStatement:
        """
        Make a block with a single statement: `lhs = rhs;`
        """
        lhs_copy = copy.deepcopy(lhs)
        expr = node_factory.create_assignment_expr(lhs_copy, rhs, AssignmentOps.EQUAL)
        stmt = node_factory.create_expression_stmt(expr)
        return node_factory.create_block_stmt(
            node_factory.create_statement_list([stmt])
        )

    # ======== Visitors ========

    def visit_SwitchStatement(
        self,
        node: SwitchStatement,
        parent: Optional[Node] = None,
        parent_attr: Optional[str] = None,
    ):
        # Transform children first (keeps behavior consistent with provided code)
        self.generic_visit(node, parent, parent_attr)

        condition = node.condition
        cases = node.cases

        # Only safe to transform when every non-default case ends with `break`
        if not self._can_transform(cases):
            return False, []

        # Remove trailing breaks now that we're building if-else
        self._remove_break_stmts(cases)

        initial = None
        prev_if = None
        final_else = None

        for c in cases.get_children():
            if c.case is None:
                # default goes to the last `else`
                final_else = node_factory.create_block_stmt(c.stmts)
                continue

            # Build `if (cond == case_value) { case_body }`
            cond_copy = copy.deepcopy(condition)
            if_cond = node_factory.create_binary_expr(cond_copy, c.case, BinaryOps.EQ)

            # Reuse block if the case already has a single block, else wrap stmts into a block
            if len(c.stmts.get_children()) == 1 and isinstance(
                c.stmts.get_child_at(0), BlockStatement
            ):
                if_body = c.stmts.get_child_at(0)
            else:
                if_body = node_factory.create_block_stmt(c.stmts)

            if_stmt = node_factory.create_if_stmt(if_cond, if_body)

            if prev_if is not None:
                prev_if.alternate = if_stmt
            else:
                initial = if_stmt

            prev_if = if_stmt

        # Attach final else (default), or degenerate case: only default present
        if prev_if is not None:
            prev_if.alternate = final_else
        else:
            # Only default existed; create a trivial if with original condition (kept for structure)
            initial = node_factory.create_if_stmt(condition, final_else)

        return True, [initial]

    def visit_ExpressionStatement(
        self,
        node: ExpressionStatement,
        parent: Optional[Node] = None,
        parent_attr: Optional[str] = None,
    ):
        # We do *not* transform children first here (follow TernaryToIfVisitor),
        # because we might replace this node with an if-statement.
        expr = node.expr
        if not isinstance(expr, AssignmentExpression):
            return False, []
        if expr.op != AssignmentOps.EQUAL:
            return False, []

        lhs = expr.left
        rhs = expr.right
        if not isinstance(rhs, TernaryExpression):
            return False, []

        condition = rhs.condition
        consequence = rhs.consequence
        alternative = rhs.alternative

        # Make:
        # if (cond) { lhs = consequence; } else { lhs = alternative; }
        then_block = self._wrap_assignment_block(lhs, consequence)
        else_block = self._wrap_assignment_block(lhs, alternative)
        new_if = node_factory.create_if_stmt(condition, then_block, else_block)

        # Also transform inside the newly created if (as in the original code)
        self.generic_visit(new_if, parent, parent_attr)

        return True, [new_if]
