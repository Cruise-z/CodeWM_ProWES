from ..nodes import Node
from .code_transformer import CodeTransformer
from ..tree_manip.visitors.default_param_trans import DefaultParamTransVisitor


class DefaultParamTransformer(CodeTransformer):
    name = "DefaultParamTransformer"
    TRANSFORM_DEFAULT_PARAM = "DefaultParamTransformer.indexof_zero"

    def __init__(self, lang: str) -> None:
        super().__init__()
        self.lang = lang

    def get_available_transforms(self):
        return [self.TRANSFORM_DEFAULT_PARAM]

    def mutable_tree_transform(self, node: Node, dst_style: str):
        if dst_style != self.TRANSFORM_DEFAULT_PARAM:
            self.throw_invalid_dst_style(dst_style)
        return DefaultParamTransVisitor(self.lang).visit(node)
