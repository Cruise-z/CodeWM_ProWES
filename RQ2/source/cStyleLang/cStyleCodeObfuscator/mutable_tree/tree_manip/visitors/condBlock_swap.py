#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
condBlock_swap.py

A combination visitor that swap condition block in C-style language ASTs.
- block_swap.py

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
    Expression,
    BinaryExpression,
    UnaryExpression,
    ParenthesizedExpression,
)
from ...nodes import BinaryOps, UnaryOps


class CondBlockSwapper(TransformingVisitor):
    """
    Swap `then`/`else` blocks of an if-statement and logically negate its condition.

    Rule:
      if (COND) { A } else { B }
      =>
      if (!COND) { B } else { A }

    Notes:
      - We require an `else` branch; otherwise there's nothing to swap.
      - Negation is done safely:
          * !( !X )  ->  X
          * a < b    ->  a >= b
          * a <= b   ->  a >  b
          * a > b    ->  a <= b
          * a >= b   ->  a <  b
          * a == b   ->  a != b
          * a != b   ->  a == b
          * other expressions -> wrap with parentheses if needed, then add '!' unary
      - Both branches are wrapped as blocks if necessary.
    """

    def _strip_parens(self, e: Expression) -> Expression:
        while isinstance(e, ParenthesizedExpression):
            e = e.expr
        return e

    def _complement(self, e: Expression) -> Expression:
        """
        Produce logical complement of expression, reusing the operator mappings
        from Normal/Negaed swappers where applicable; otherwise use UnaryOps.NOT.
        """
        e0 = self._strip_parens(e)

        # Binary relational/equality operators: map to their complements
        if isinstance(e0, BinaryExpression):
            comp_map = {
                BinaryOps.LT: BinaryOps.GE,
                BinaryOps.LE: BinaryOps.GT,
                BinaryOps.GT: BinaryOps.LE,
                BinaryOps.GE: BinaryOps.LT,
                BinaryOps.EQ: BinaryOps.NE,
                BinaryOps.NE: BinaryOps.EQ,
            }
            if e0.op in comp_map:
                return node_factory.create_binary_expr(e0.left, e0.right, comp_map[e0.op])

        # Double negation: !( !X ) => X
        if isinstance(e0, UnaryExpression) and e0.op == UnaryOps.NOT:
            return e0.operand

        # Fallback: !(expr) (parenthesize complex expressions for clarity/precedence)
        if e0.node_type not in {
            NodeType.CALL_EXPR,
            NodeType.IDENTIFIER,
            NodeType.LITERAL,
            NodeType.UNARY_EXPR,
        }:
            e0 = node_factory.create_parenthesized_expr(e0)
        return node_factory.create_unary_expr(e0, UnaryOps.NOT)

    def visit_IfStatement(
        self,
        node: IfStatement,
        parent: Optional[Node] = None,
        parent_attr: Optional[str] = None,
    ):
        # visit children first to stay consistent with other visitors
        self.generic_visit(node, parent, parent_attr)

        # must have an else-branch to swap
        if node.alternate is None:
            return False, []

        # complement condition
        new_condition = self._complement(node.condition)

        # ensure both arms are blocks
        then_block = node.consequence
        else_block = node.alternate
        if then_block.node_type != NodeType.BLOCK_STMT:
            then_block = node_factory.wrap_block_stmt(then_block)
        if else_block.node_type != NodeType.BLOCK_STMT:
            else_block = node_factory.wrap_block_stmt(else_block)

        # swap branches
        new_if = node_factory.create_if_stmt(new_condition, else_block, then_block)
        return True, [new_if]
