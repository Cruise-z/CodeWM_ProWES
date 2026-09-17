from ..nodes import Node
from .code_transformer import CodeTransformer
from ..tree_manip.visitors import IdRenameVisitor


class IdRenameTransformer(CodeTransformer):
    name = "IdRenameTransformer"
    TRANSFORM_ID_RENAME = "IdRenameTransformer.id_rename"

    def __init__(self, seed=None) -> None:
        super().__init__()
        self.seed = seed

    def get_available_transforms(self):
        return [self.TRANSFORM_ID_RENAME]

    def mutable_tree_transform(self, node: Node, dst_style: str):
        return {
            self.TRANSFORM_ID_RENAME: IdRenameVisitor(seed=self.seed),
        }[dst_style].visit(node)
