# pyCodeObfuscator/patterns/AL/expression/op_opequal_usage_pattern.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import libcst as cst


class OpOrOpEqualUsageForm(str, Enum):
    """
    两种「写法风格」：
    - OP_EQUAL  : 使用复合赋值（x += y / x -= y / x *= y / x /= y）
    - OP_ASSIGN : 使用普通赋值（x = x + y / x = x - y ...）

    注意：虽然名字里是 Op/OpEqual，但已经拓展到 + - * / 四种运算。
    """
    OP_EQUAL = "opequal"      # 复合赋值风格
    OP_ASSIGN = "op_assign"   # 显式二元表达式赋值风格


class OpOrOpEqualOpKind(str, Enum):
    """
    支持的运算符种类。
    """
    ADD = "add"  # +
    SUB = "sub"  # -
    MUL = "mul"  # *
    DIV = "div"  # /


@dataclass
class OpOrOpEqualUsageMatch:
    """
    一次命中的信息：
      - form    : 写法风格（OP_EQUAL / OP_ASSIGN）
      - op_kind : 使用的运算符种类（ADD / SUB / MUL / DIV）
      - stmt    : 整个简单语句行（SimpleStatementLine）
      - target  : 被更新的变量（目前只匹配简单 Name）
      - delta   : 增量/变化量表达式
    """
    form: OpOrOpEqualUsageForm
    op_kind: OpOrOpEqualOpKind
    stmt: cst.SimpleStatementLine
    target: cst.BaseExpression
    delta: cst.BaseExpression


def _detect_augassign_op_kind(
    op: cst.BaseAugOp,
) -> Optional[OpOrOpEqualOpKind]:
    """
    将 AugAssign 的 operator 映射到我们自己的 op_kind 枚举。
    只支持 + - * / 四种。
    """
    if isinstance(op, cst.AddAssign):
        return OpOrOpEqualOpKind.ADD
    if isinstance(op, cst.SubtractAssign):
        return OpOrOpEqualOpKind.SUB
    if isinstance(op, cst.MultiplyAssign):
        return OpOrOpEqualOpKind.MUL
    if isinstance(op, cst.DivideAssign):
        return OpOrOpEqualOpKind.DIV
    return None


def _detect_binary_op_kind(
    op: cst.BaseBinaryOp,
) -> Optional[OpOrOpEqualOpKind]:
    """
    将 BinaryOperation 的 operator 映射到 op_kind 枚举。
    同样只支持 + - * /。
    """
    if isinstance(op, cst.Add):
        return OpOrOpEqualOpKind.ADD
    if isinstance(op, cst.Subtract):
        return OpOrOpEqualOpKind.SUB
    if isinstance(op, cst.Multiply):
        return OpOrOpEqualOpKind.MUL
    if isinstance(op, cst.Divide):
        return OpOrOpEqualOpKind.DIV
    return None


def _match_augassign(
    stmt: cst.SimpleStatementLine,
) -> Optional[OpOrOpEqualUsageMatch]:
    # 只处理「单一小语句」的情况
    if len(stmt.body) != 1:
        return None

    small = stmt.body[0]
    if not isinstance(small, cst.AugAssign):
        return None

    op_kind = _detect_augassign_op_kind(small.operator)
    if op_kind is None:
        return None

    target = small.target
    # 保守起见，目前只匹配简单变量名：x += y / x -= y ...
    if not isinstance(target, cst.Name):
        return None

    return OpOrOpEqualUsageMatch(
        form=OpOrOpEqualUsageForm.OP_EQUAL,
        op_kind=op_kind,
        stmt=stmt,
        target=target,
        delta=small.value,
    )


def _match_assign(
    stmt: cst.SimpleStatementLine,
) -> Optional[OpOrOpEqualUsageMatch]:
    if len(stmt.body) != 1:
        return None

    small = stmt.body[0]
    if not isinstance(small, cst.Assign):
        return None

    # 只处理单一目标：x = ...
    if len(small.targets) != 1:
        return None

    assign_target = small.targets[0]
    target_expr = assign_target.target

    # 同样只匹配简单变量名：x = ...
    if not isinstance(target_expr, cst.Name):
        return None

    value = small.value
    if not isinstance(value, cst.BinaryOperation):
        return None

    op_kind = _detect_binary_op_kind(value.operator)
    if op_kind is None:
        return None

    # 对所有运算符一视同仁，只接受 x = x <op> delta 形式
    if not target_expr.deep_equals(value.left):
        return None

    delta = value.right

    return OpOrOpEqualUsageMatch(
        form=OpOrOpEqualUsageForm.OP_ASSIGN,
        op_kind=op_kind,
        stmt=stmt,
        target=target_expr,
        delta=delta,
    )


def match_op_opequal_usage(
    node: cst.CSTNode,
) -> Optional[OpOrOpEqualUsageMatch]:
    """
    顶层匹配入口。

    目前只在 SimpleStatementLine 上工作：
      - x += y / x -= y / x *= y / x /= y
      - x = x + y / x = x - y / x = x * y / x = x / y
    """
    if not isinstance(node, cst.SimpleStatementLine):
        return None

    # 先尝试匹配复合赋值形态
    m = _match_augassign(node)
    if m is not None:
        return m

    # 再尝试匹配「显式二元表达式」形态
    return _match_assign(node)
