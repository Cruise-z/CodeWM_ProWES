from ..nodes import Node
from .code_transformer import CodeTransformer
from ..tree_manip.visitors import ConditionTransVisitor


class ConditionTransformer(CodeTransformer):
    name = "ConditionTransformer"
    # TRANSFORM_COND_SWITCH = "ConditionTransformer.switch"
    # TRANSFORM_COND_TERNARY = "ConditionTransformer.ternary"
    TRANSFORM_COND_TOIF = "ConditionTransformer.ToIf"

    def __init__(self) -> None:
        super().__init__()

    def get_available_transforms(self):
        # return [self.TRANSFORM_COND_SWITCH, self.TRANSFORM_COND_TERNARY]
        return [self.TRANSFORM_COND_TOIF]

    def mutable_tree_transform(self, node: Node, dst_style: str):
        return {
            # self.TRANSFORM_COND_SWITCH: SwitchToIfVisitor(),
            # self.TRANSFORM_COND_TERNARY: TernaryToIfVisitor(),
            self.TRANSFORM_COND_TOIF: ConditionTransVisitor(),
        }[dst_style].visit(node)
