# pyCodeObfuscator/rules/AL/expression/op_opequal_usage.py
from __future__ import annotations

from typing import Dict, Optional

import libcst as cst

from ....core.rule_base import BaseRule, RuleDirection, register_rule
from ....patterns.AL.expression.op_opequal_usage_pattern import (
    OpOrOpEqualUsageForm,
    OpOrOpEqualOpKind,
    OpOrOpEqualUsageMatch,
    match_op_opequal_usage,
)


# variant 名到「风格形态」的映射
# 为了兼容老配置，这里顺带保留 addequal / add_assign 这些旧名字。
_VARIANT_KEY_TO_FORM: Dict[str, OpOrOpEqualUsageForm] = {
    # 新命名
    "opequal": OpOrOpEqualUsageForm.OP_EQUAL,
    "op_assign": OpOrOpEqualUsageForm.OP_ASSIGN,
    "binary": OpOrOpEqualUsageForm.OP_ASSIGN,
    "explicit": OpOrOpEqualUsageForm.OP_ASSIGN,
    "augassign": OpOrOpEqualUsageForm.OP_EQUAL,
    # 兼容旧命名
    "addequal": OpOrOpEqualUsageForm.OP_EQUAL,
    "add_assign": OpOrOpEqualUsageForm.OP_ASSIGN,
}


def _make_binary_op(op_kind: OpOrOpEqualOpKind) -> cst.BaseBinaryOp:
    """
    根据 op_kind 构造 BinaryOperation 的 operator。
    """
    if op_kind is OpOrOpEqualOpKind.ADD:
        return cst.Add()
    if op_kind is OpOrOpEqualOpKind.SUB:
        return cst.Subtract()
    if op_kind is OpOrOpEqualOpKind.MUL:
        return cst.Multiply()
    if op_kind is OpOrOpEqualOpKind.DIV:
        return cst.Divide()
    # 理论上不会走到这里
    raise ValueError(f"Unsupported op_kind for BinaryOperation: {op_kind!r}")


def _make_augassign_op(op_kind: OpOrOpEqualOpKind) -> cst.BaseAugOp:
    """
    根据 op_kind 构造 AugAssign 的 operator。
    """
    if op_kind is OpOrOpEqualOpKind.ADD:
        return cst.AddAssign()
    if op_kind is OpOrOpEqualOpKind.SUB:
        return cst.SubtractAssign()
    if op_kind is OpOrOpEqualOpKind.MUL:
        return cst.MultiplyAssign()
    if op_kind is OpOrOpEqualOpKind.DIV:
        return cst.DivideAssign()
    raise ValueError(f"Unsupported op_kind for AugAssign: {op_kind!r}")


def _rewrite_opequal_to_op_assign(
    match: OpOrOpEqualUsageMatch,
) -> cst.SimpleStatementLine:
    """
    x <op>= y   ->   x = x <op> y
    """
    new_small = cst.Assign(
        targets=[cst.AssignTarget(target=match.target)],
        value=cst.BinaryOperation(
            left=match.target,
            operator=_make_binary_op(match.op_kind),
            right=match.delta,
        ),
    )
    return match.stmt.with_changes(body=[new_small])


def _rewrite_op_assign_to_opequal(
    match: OpOrOpEqualUsageMatch,
) -> cst.SimpleStatementLine:
    """
    x = x <op> y   ->   x <op>= y
    """
    new_small = cst.AugAssign(
        target=match.target,
        operator=_make_augassign_op(match.op_kind),
        value=match.delta,
    )
    return match.stmt.with_changes(body=[new_small])


@register_rule
class OpOrOpEqualUsageRule(BaseRule):
    """
    Refactoring: Usage of op / opequal.

    在下面两种风格之间互转：
      - x += y / x -= y / x *= y / x /= y
      - x = x + y / x = x - y / x = x * y / x = x / y
    """

    rule_id = "refactoring.op_or_opequal_usage"
    description = (
        "Refactor between `x <op>= y` and `x = x <op> y` styles "
        "for + - * / operators."
    )
    # 暴露给 CLI / 配置使用的「官方」变体名
    variants = ("opequal", "op_assign")

    def _target_form_for(
        self, current: OpOrOpEqualUsageForm
    ) -> Optional[OpOrOpEqualUsageForm]:
        """
        根据当前形态 + RuleDirection 决定目标形态。
        返回 None 表示“不需要改写”。
        """
        direction = self.direction

        if direction.mode == "AUTO":
            # AUTO：两种形态互相翻转
            if current is OpOrOpEqualUsageForm.OP_EQUAL:
                target = OpOrOpEqualUsageForm.OP_ASSIGN
            elif current is OpOrOpEqualUsageForm.OP_ASSIGN:
                target = OpOrOpEqualUsageForm.OP_EQUAL
            else:
                return None

        elif direction.mode == "TO_VARIANT":
            key = direction.variant
            if key is None:
                return None
            form = _VARIANT_KEY_TO_FORM.get(key.lower())
            if form is None:
                return None
            target = form

        else:
            return None

        # 目标和当前一样就不用改写
        if target is current:
            return None

        return target

    def leave_SimpleStatementLine(
        self,
        original_node: cst.SimpleStatementLine,
        updated_node: cst.SimpleStatementLine,
    ) -> cst.SimpleStatementLine:
        match = match_op_opequal_usage(updated_node)
        if match is None:
            return updated_node

        target_form = self._target_form_for(match.form)
        if target_form is None:
            return updated_node

        # x <op>= y  ->  x = x <op> y
        if (
            match.form is OpOrOpEqualUsageForm.OP_EQUAL
            and target_form is OpOrOpEqualUsageForm.OP_ASSIGN
        ):
            return _rewrite_opequal_to_op_assign(match)

        # x = x <op> y  ->  x <op>= y
        if (
            match.form is OpOrOpEqualUsageForm.OP_ASSIGN
            and target_form is OpOrOpEqualUsageForm.OP_EQUAL
        ):
            return _rewrite_op_assign_to_opequal(match)

        return updated_node
