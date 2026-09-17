from .visitor import TransformingVisitor
from ...nodes import Node
from ...nodes import node_factory
from ...nodes import WhileStatement
from typing import Optional


class WhileToForVisitor(TransformingVisitor):
    def visit_WhileStatement(
        self,
        node: WhileStatement,
        parent: Optional[Node] = None,
        parent_attr: Optional[str] = None,
    ):
        self.generic_visit(node, parent, parent_attr)
        new_stmts = []
        condition = node.condition
        body = node.body

        for_stmt = node_factory.create_for_stmt(body, condition=condition)
        new_stmts.append(for_stmt)

        return (True, new_stmts)
