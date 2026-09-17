from ..nodes import Node
from .code_transformer import CodeTransformer
from ..tree_manip.visitors.equivalent_forms_trans import EquivalentFormsTransVisitor


class EquivalentFormsTransformer(CodeTransformer):
    name = "EquivalentFormsTransformer"
    TRANSFORM_EQUIVALENT_FORMS = "EquivalentFormsTransformer.safe_equiv"

    def __init__(self, lang: str) -> None:
        super().__init__()
        self.lang = lang

    def get_available_transforms(self):
        return [self.TRANSFORM_EQUIVALENT_FORMS]

    def mutable_tree_transform(self, node: Node, dst_style: str):
        if dst_style != self.TRANSFORM_EQUIVALENT_FORMS:
            self.throw_invalid_dst_style(dst_style)
        return EquivalentFormsTransVisitor(self.lang).visit(node)
