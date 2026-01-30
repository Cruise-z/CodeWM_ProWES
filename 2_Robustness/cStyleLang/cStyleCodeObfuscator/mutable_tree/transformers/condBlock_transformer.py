from ..nodes import Node
from .code_transformer import CodeTransformer
from ..tree_manip.visitors import CondBlockSwapper


class CondBlockSwapTransformer(CodeTransformer):
    name = "CondBlockSwapTransformer"
    TRANSFORM_IF_BLOCK_SWAP = "CondBlockSwapTransformer.block_swap"

    def __init__(self) -> None:
        super().__init__()

    def get_available_transforms(self):
        return [self.TRANSFORM_IF_BLOCK_SWAP]

    def mutable_tree_transform(self, node: Node, dst_style: str):
        return {
            self.TRANSFORM_IF_BLOCK_SWAP: CondBlockSwapper(),
        }[dst_style].visit(node)
