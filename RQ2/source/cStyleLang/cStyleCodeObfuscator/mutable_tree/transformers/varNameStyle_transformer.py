from ..nodes import Node
from .code_transformer import CodeTransformer
from ..tree_manip.visitors import (
    VarNameStyleTransVisitor,
)


class VarNameStyleTransformer(CodeTransformer):
    name = "VarNameStyleTransformer"
    TRANSFORM_VARNAME_STYLE = "VarNameStyleTransformer.varname_style"

    def __init__(self, seed=None) -> None:
        super().__init__()
        self.seed = seed

    def get_available_transforms(self):
        return [
            self.TRANSFORM_VARNAME_STYLE,
        ]

    def mutable_tree_transform(self, node: Node, dst_style: str):
        return {
            self.TRANSFORM_VARNAME_STYLE: VarNameStyleTransVisitor(seed=self.seed),
        }[dst_style].visit(node)
