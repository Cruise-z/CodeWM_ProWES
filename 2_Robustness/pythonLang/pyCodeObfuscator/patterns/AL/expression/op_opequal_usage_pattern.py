# pyCodeObfuscator/patterns/AL/expression/op_opequal_usage_pattern.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import libcst as cst


class OpOrOpEqualUsageForm(str, Enum):
    """
    Two syntax styles:
    - OP_EQUAL  : use augmented assignment (x += y / x -= y / x *= y / x /= y)
    - OP_ASSIGN : use regular assignment (x = x + y / x = x - y ...)

    Note: although the name mentions Op/OpEqual, it has already been extended to the four operators + - * /.
    """
    OP_EQUAL = "opequal"      # augmented-assignment style
    OP_ASSIGN = "op_assign"   # explicit binary-expression assignment style


class OpOrOpEqualOpKind(str, Enum):
    """
    Supported operator kinds.
    """
    ADD = "add"  # +
    SUB = "sub"  # -
    MUL = "mul"  # *
    DIV = "div"  # /


@dataclass
class OpOrOpEqualUsageMatch:
    """
    Information for a single match:
      - form    : syntax style (OP_EQUAL / OP_ASSIGN)
      - op_kind : operator kind used (ADD / SUB / MUL / DIV)
      - stmt    : the whole SimpleStatementLine
      - target  : the variable being updated (currently only simple Name is matched)
      - delta   : increment/change expression
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
    Map an AugAssign operator to the internal op_kind enum.
    Only + - * / are supported.
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
    Map a BinaryOperation operator to the op_kind enum.
    Again, only + - * / are supported.
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
    # Only handle the case of a single small statement
    if len(stmt.body) != 1:
        return None

    small = stmt.body[0]
    if not isinstance(small, cst.AugAssign):
        return None

    op_kind = _detect_augassign_op_kind(small.operator)
    if op_kind is None:
        return None

    target = small.target
    # Conservatively, only match simple variable names for now: x += y / x -= y ...
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

    # Only handle a single target: x = ...
    if len(small.targets) != 1:
        return None

    assign_target = small.targets[0]
    target_expr = assign_target.target

    # Again, only match simple variable names: x = ...
    if not isinstance(target_expr, cst.Name):
        return None

    value = small.value
    if not isinstance(value, cst.BinaryOperation):
        return None

    op_kind = _detect_binary_op_kind(value.operator)
    if op_kind is None:
        return None

    # Treat all supported operators uniformly and only accept the form x = x <op> delta
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
    Top-level matching entry point.

    Currently this only works on SimpleStatementLine:
      - x += y / x -= y / x *= y / x /= y
      - x = x + y / x = x - y / x = x * y / x = x / y
    """
    if not isinstance(node, cst.SimpleStatementLine):
        return None

    # Try the augmented-assignment form first
    m = _match_augassign(node)
    if m is not None:
        return m

    # Then try the explicit binary-expression form
    return _match_assign(node)
