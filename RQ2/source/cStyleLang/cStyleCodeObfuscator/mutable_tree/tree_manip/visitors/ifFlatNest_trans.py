#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ifFlatNest_trans.py

A combination visitor that trans if compound&nest statement in C-style language ASTs.
- compound_if.py
- nested_if.py

Author: Cruise-z <cruise.zrz@gmail.com>
Affiliation: IIE CAS
Date: 2025-11-07
"""
from typing import Optional

from .visitor import TransformingVisitor
from ...nodes import (
    Node,
    NodeType,
    node_factory,
    IfStatement,
    BlockStatement,
    Expression,
    BinaryExpression,
    BinaryOps,
    ParenthesizedExpression,
)


class IfFlatNestTransVisitor(TransformingVisitor):
    """
    A unified If<->If-AND transformer.

    - If it sees a *nested-if* with no else:
        if (A) {
          if (B) { S; }
        }
      → if (A && B) { S; }

    - If it sees a *compound-if* (A && B) with no else:
        if (A && B) { S; }
      → if (A) { if (B) { S; } }
    """

    # -------- helpers reused from CompoundIfVisitor --------

    def _create_logical_and(self, lhs: Expression, rhs: Expression) -> BinaryExpression:
        # Parenthesize non-singleton expressions for readability/precedence
        singleton_types = {
            NodeType.LITERAL,
            NodeType.IDENTIFIER,
            NodeType.CALL_EXPR,
            NodeType.PARENTHESIZED_EXPR,
        }
        if lhs.node_type not in singleton_types:
            lhs = node_factory.create_parenthesized_expr(lhs)
        if rhs.node_type not in singleton_types:
            rhs = node_factory.create_parenthesized_expr(rhs)
        return node_factory.create_binary_expr(lhs, rhs, BinaryOps.AND)

    def _find_nested_if(self, node: IfStatement) -> Optional[IfStatement]:
        # Only handle: outer if has no else
        if node.alternate is not None:
            return None

        body = node.consequence
        # Body is a block with exactly one stmt which is an if (with no else)
        if isinstance(body, BlockStatement):
            stmts = body.stmts.get_children()
            if len(stmts) != 1:
                return None
            if not isinstance(stmts[0], IfStatement):
                return None
            if stmts[0].alternate is not None:
                return None
            nested_if = stmts[0]
        # Body itself is an if (with no else)
        elif isinstance(body, IfStatement):
            if body.alternate is not None:
                return None
            nested_if = body
        else:
            return None

        return nested_if

    # -------- main transform --------

    def visit_IfStatement(
        self,
        node: IfStatement,
        parent: Optional[Node] = None,
        parent_attr: Optional[str] = None,
    ):
        # Transform children first (consistent with provided visitors)
        self.generic_visit(node, parent, parent_attr)

        # 1) Nested-if -> Compound-if
        candidate = self._find_nested_if(node)
        if candidate is not None:
            cond_1 = node.condition
            cond_2 = candidate.condition
            if_cond = self._create_logical_and(cond_1, cond_2)
            if_body = candidate.consequence
            if_alt = candidate.alternate  # should be None by contract
            merged_if = node_factory.create_if_stmt(if_cond, if_body, if_alt)
            return True, [merged_if]

        # 2) Compound-if (A && B) -> Nested-if  (only when no else)
        if node.alternate is None and isinstance(node.condition, BinaryExpression):
            cond_bin = node.condition
            if cond_bin.op == BinaryOps.AND:
                cond_1 = cond_bin.left
                cond_2 = cond_bin.right

                # Strip outer parentheses (for readability), as in NestedIfVisitor
                if isinstance(cond_1, ParenthesizedExpression):
                    cond_1 = cond_1.expr
                if isinstance(cond_2, ParenthesizedExpression):
                    cond_2 = cond_2.expr

                inner_if = node_factory.create_if_stmt(cond_2, node.consequence)
                inner_block = node_factory.wrap_block_stmt(inner_if)
                outer_if = node_factory.create_if_stmt(cond_1, inner_block)
                return True, [outer_if]

        # No change
        return False, []
