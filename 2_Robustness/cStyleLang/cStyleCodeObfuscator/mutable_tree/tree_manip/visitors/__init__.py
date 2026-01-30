# base
from .visitor import Visitor, TransformingVisitor, StatefulTransformingVisitor

# loop transformers
# from .loop_while import ForToWhileVisitor
# from .loop_for import WhileToForVisitor
from .loopStmt_trans import LoopStmtTransVisitor

# increment/decrement transformers
# from .update_prefix import PrefixUpdateVisitor
# from .update_postfix import PostfixUpdateVisitor
# from .update_assign import AssignUpdateVisitor
# from .update_binop import BinopUpdateVisitor
from .update_trans import UpdateTransVisitor

# condition transformers
# from .ternary_to_if import TernaryToIfVisitor
# from .switch_to_if import SwitchToIfVisitor
from .condition_trans import ConditionTransVisitor
# from .compound_if import CompoundIfVisitor
# from .nested_if import NestedIfVisitor
from .ifFlatNest_trans import IfFlatNestTransVisitor

# naming transformers
# from .var_naming_style import (
#     ToCamelCaseVisitor,
#     ToPascalCaseVisitor,
#     ToSnakeCaseVisitor,
#     ToUnderscoreCaseVisitor,
# )
from .varNameStyle_trans import VarNameStyleTransVisitor
# from .identifier_rename import IdentifierRenamingVisitor, IdentifierAppendingVisitor
from .idRename import IdRenameVisitor

# variable decl transformers
# from .var_same_type import SplitVarWithSameTypeVisitor, MergeVarWithSameTypeVisitor
# from .var_pos import MoveVarDeclToHeadVisitor, MoveVarDeclToBeforeUsedVisitor
# from .var_init import SplitVarInitAndDeclVisitor, MergeVarInitAndDeclVisitor
from .repos_varDecl import ReposVarDeclVisitor

# block swap
# from .block_swap import NormalBlockSwapper, NegatedBlockSwapper
from .condBlock_swap import CondBlockSwapper

# infinite loop condition
# from .loop_condition import LoopLiteralOneVisitor, LoopLiteralTrueVisitor
from .loopCond_trans import LoopCondTransVisitor
