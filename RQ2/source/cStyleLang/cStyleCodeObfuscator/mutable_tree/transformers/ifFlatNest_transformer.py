from ..nodes import Node
from .code_transformer import CodeTransformer
from ..tree_manip.visitors import IfFlatNestTransVisitor


class IfFlatNestTransformer(CodeTransformer):
    name = "IfFlatNestTransformer"
    TRANSFORM_IF_FlatNest = "IfFlatNestTransformer.if_compound_nest"

    def __init__(self) -> None:
        super().__init__()

    def get_available_transforms(self):
        return [self.TRANSFORM_IF_FlatNest]

    def mutable_tree_transform(self, node: Node, dst_style: str):
        return {
            self.TRANSFORM_IF_FlatNest: IfFlatNestTransVisitor(),
        }[dst_style].visit(node)
