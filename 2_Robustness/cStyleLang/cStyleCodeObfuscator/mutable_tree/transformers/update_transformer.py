from ..nodes import Node
from .code_transformer import CodeTransformer
from ..tree_manip.visitors import (
    # PrefixUpdateVisitor,
    # PostfixUpdateVisitor,
    # BinopUpdateVisitor,
    # AssignUpdateVisitor,
    UpdateTransVisitor,
)


class UpdateTransformer(CodeTransformer):
    name = "UpdateTransformer"
    # TRANSFORM_PREFIX_UPDATE = "UpdateTransformer.prefix_update"
    # TRANSFORM_POSTFIX_UPDATE = "UpdateTransformer.postfix_update"
    # TRANSFORM_BINOP_UPDATE = "UpdateTransformer.binop_update"
    # TRANSFORM_ASSIGN_UPDATE = "UpdateTransformer.assign_update"
    TRANSFORM_VAREXP_UPDATE = "UpdateTransformer.varexp_update"

    def __init__(self) -> None:
        super().__init__()

    def get_available_transforms(self):
        return [
            # self.TRANSFORM_PREFIX_UPDATE,
            # self.TRANSFORM_POSTFIX_UPDATE,
            # self.TRANSFORM_BINOP_UPDATE,
            # self.TRANSFORM_ASSIGN_UPDATE,
            self.TRANSFORM_VAREXP_UPDATE,
        ]

    def mutable_tree_transform(self, node: Node, dst_style: str):
        return {
            # self.TRANSFORM_PREFIX_UPDATE: PrefixUpdateVisitor(),
            # self.TRANSFORM_POSTFIX_UPDATE: PostfixUpdateVisitor(),
            # self.TRANSFORM_BINOP_UPDATE: BinopUpdateVisitor(),
            # self.TRANSFORM_ASSIGN_UPDATE: AssignUpdateVisitor(),
            self.TRANSFORM_VAREXP_UPDATE: UpdateTransVisitor(),
        }[dst_style].visit(node)
