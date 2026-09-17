from ..nodes import Node
from .code_transformer import CodeTransformer
from ..tree_manip.visitors import LoopStmtTransVisitor


class LoopStmtTransformer(CodeTransformer):
    name = "LoopStmtTransformer"
    TRANSFORM_LOOP_STMT = "LoopStmtTransformer.loop_stmt"

    def __init__(self) -> None:
        super().__init__()

    def get_available_transforms(self):
        return [self.TRANSFORM_LOOP_STMT]

    def mutable_tree_transform(self, node: Node, dst_style: str):
        return {
            self.TRANSFORM_LOOP_STMT: LoopStmtTransVisitor(),
        }[dst_style].visit(node)
