#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
loopStmt_trans.py

A combination visitor that trans loop statement in C-style language ASTs.
- loop_for.py
- loop_while.py

Author: Cruise-z <cruise.zrz@gmail.com>
Affiliation: IIE CAS
Date: 2025-10-29
"""
from typing import Optional, List, Tuple

from .visitor import TransformingVisitor
from ...nodes import (
    Node,
    NodeType,
    NodeList,
    Statement,
    ForStatement,
    WhileStatement,
    ContinueStatement,
)
from ...nodes import node_factory, is_expression


class LoopStmtTransVisitor(TransformingVisitor):
    """
    A unified loop statement transformer:
      - If encountering a ForStatement, convert it to a WhileStatement
        while preserving semantics (move init before loop, append update
        at the end of body and before each 'continue' in the same loop scope).
      - If encountering a WhileStatement, convert it to a ForStatement
        with condition in the for's middle field (init/update left empty).
    """

    # ---------- Helpers reused (and slightly sanitized) from your For->While logic ----------

    def _wrap_loop_body(self, body_stmts: List[Statement]) -> Statement:
        """Remove empty statements and wrap the sequence into a block stmt."""
        # safer removal than mutating while iterating
        pruned = [s for s in body_stmts if s.node_type != NodeType.EMPTY_STMT]
        if not pruned:
            return node_factory.create_empty_stmt()
        stmt_list = node_factory.create_statement_list(pruned)
        return node_factory.create_block_stmt(stmt_list)

    def _collect_continue_stmts(self, node: Node, parent: Optional[Node] = None) -> List[Tuple[Node, Optional[Node]]]:
        """Collect `continue` statements that are in the same loop scope (do not descend into nested loops)."""
        if isinstance(node, ContinueStatement):
            return [(node, parent)]
        results: List[Tuple[Node, Optional[Node]]] = []
        for child_attr in node.get_children_names():
            child = node.get_child_at(child_attr)
            # only collect in the same scope: stop descending into nested loops
            if child is not None and not isinstance(child, ForStatement) and not isinstance(child, WhileStatement):
                results += self._collect_continue_stmts(child, node)
        return results

    # ---------- for -> while ----------

    def visit_ForStatement(
        self,
        node: ForStatement,
        parent: Optional[Node] = None,
        parent_attr: Optional[str] = None,
    ):
        # transform children first (consistent with your original visitors)
        self.generic_visit(node, parent, parent_attr)

        new_stmts: List[Statement] = []
        init = node.init
        condition = node.condition
        update = node.update
        body = node.body

        # 1) move init before loop
        if init is not None:
            if init.node_type == NodeType.EXPRESSION_LIST:
                # promote expressions to standalone statements
                for init_expr in init.get_children():
                    new_stmts.append(node_factory.create_expression_stmt(init_expr))
            else:
                new_stmts.append(init)

        # 2) extract condition/update/body
        if condition is None:
            condition = node_factory.create_literal("true")

        update_exprs = update.get_children() if update is not None else []

        if body.node_type != NodeType.BLOCK_STMT:
            body_stmts = [body]
        else:
            # get statement list from block statement
            body_stmts = body.get_children()[0].get_children()

        # 3) append update-exprs as trailing statements in the loop body
        for u in update_exprs:
            assert is_expression(u)
            body_stmts.append(node_factory.create_expression_stmt(u))

        # 4) insert updates before every `continue` in the same loop scope
        continues = self._collect_continue_stmts(body)
        for cont_node, cont_parent in continues:
            if isinstance(cont_parent, NodeList):
                new_node_list: List[Statement] = []
                for child_attr in cont_parent.get_children_names():
                    child = cont_parent.get_child_at(child_attr)
                    if child is not None:
                        if child is cont_node:
                            for u in update_exprs:
                                assert is_expression(u)
                                new_node_list.append(node_factory.create_expression_stmt(u))
                            new_node_list.append(cont_node)
                        else:
                            new_node_list.append(child)
                cont_parent.node_list = new_node_list
            else:
                # wrap: { update; continue; }
                continue_block_stmts: List[Statement] = []
                for u in update_exprs:
                    assert is_expression(u)
                    continue_block_stmts.append(node_factory.create_expression_stmt(u))
                continue_block_stmts.append(cont_node)
                block_stmt = node_factory.create_block_stmt(
                    node_factory.create_statement_list(continue_block_stmts)
                )

                for child_attr in cont_parent.get_children_names():
                    child = cont_parent.get_child_at(child_attr)
                    if child is not None and child is cont_node:
                        cont_parent.set_child_at(child_attr, block_stmt)

        # 5) pack while loop
        while_body = self._wrap_loop_body(body_stmts)
        while_stmt = node_factory.create_while_stmt(condition, while_body)

        new_stmts.append(while_stmt)
        new_block = node_factory.create_block_stmt(
            node_factory.create_statement_list(new_stmts)
        )
        return True, [new_block]

    # ---------- while -> for ----------

    def visit_WhileStatement(
        self,
        node: WhileStatement,
        parent: Optional[Node] = None,
        parent_attr: Optional[str] = None,
    ):
        # transform children first
        self.generic_visit(node, parent, parent_attr)

        condition = node.condition
        body = node.body
        # create for with only condition field; init/update are None
        for_stmt = node_factory.create_for_stmt(body, condition=condition)
        return True, [for_stmt]
