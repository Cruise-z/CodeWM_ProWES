from ..nodes import Node
from .code_transformer import CodeTransformer
from ..tree_manip.visitors import (
    ReposVarDeclVisitor,
)


class ReposVarDeclTransformer(CodeTransformer):
    name = "ReposVarDeclTransformer"
    TRANSFORM_VARDECL_RANDOM = "ReposVarDeclTransformer.random_pos"

    def __init__(self) -> None:
        super().__init__()

    def get_available_transforms(self):
        return [
            self.TRANSFORM_VARDECL_RANDOM,
        ]

    def mutable_tree_transform(self, node: Node, dst_style: str):
        return {
            self.TRANSFORM_VARDECL_RANDOM: ReposVarDeclVisitor(),
        }[dst_style].visit(node)