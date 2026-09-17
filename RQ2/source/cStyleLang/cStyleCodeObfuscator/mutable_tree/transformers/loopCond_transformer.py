from ..nodes import Node
from .code_transformer import CodeTransformer
from ..tree_manip.visitors import LoopCondTransVisitor


class LoopCondTransformer(CodeTransformer):
    name = "LoopCondTransformer"
    TRANSFORM_INFLOOP_COND = "LoopCondTransformer.cond_trans"

    def __init__(self, seed=None, lang=None) -> None:
        super().__init__()
        self.seed = seed
        self.lang = lang

    def get_available_transforms(self):
        return [self.TRANSFORM_INFLOOP_COND]

    def mutable_tree_transform(self, node: Node, dst_style: str):
        return {
            self.TRANSFORM_INFLOOP_COND: LoopCondTransVisitor(seed=self.seed, lang=self.lang),
        }[dst_style].visit(node)
