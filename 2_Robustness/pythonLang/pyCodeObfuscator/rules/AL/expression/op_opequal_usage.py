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


# Mapping from variant names to style forms.
# Keep legacy names such as addequal / add_assign for compatibility with older
# configs.
_VARIANT_KEY_TO_FORM: Dict[str, OpOrOpEqualUsageForm] = {
    # New names
    "opequal": OpOrOpEqualUsageForm.OP_EQUAL,
    "op_assign": OpOrOpEqualUsageForm.OP_ASSIGN,
    "binary": OpOrOpEqualUsageForm.OP_ASSIGN,
    "explicit": OpOrOpEqualUsageForm.OP_ASSIGN,
    "augassign": OpOrOpEqualUsageForm.OP_EQUAL,
    # Backward-compatible legacy names
    "addequal": OpOrOpEqualUsageForm.OP_EQUAL,
    "add_assign": OpOrOpEqualUsageForm.OP_ASSIGN,
}


def _make_binary_op(op_kind: OpOrOpEqualOpKind) -> cst.BaseBinaryOp:
    """
    Build the BinaryOperation operator from op_kind.
    """
    if op_kind is OpOrOpEqualOpKind.ADD:
        return cst.Add()
    if op_kind is OpOrOpEqualOpKind.SUB:
        return cst.Subtract()
    if op_kind is OpOrOpEqualOpKind.MUL:
        return cst.Multiply()
    if op_kind is OpOrOpEqualOpKind.DIV:
        return cst.Divide()
    # Should not happen in practice.
    raise ValueError(f"Unsupported op_kind for BinaryOperation: {op_kind!r}")


def _make_augassign_op(op_kind: OpOrOpEqualOpKind) -> cst.BaseAugOp:
    """
    Build the AugAssign operator from op_kind.
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

    Convert between the following two styles:
      - x += y / x -= y / x *= y / x /= y
      - x = x + y / x = x - y / x = x * y / x = x / y
    """

    rule_id = "refactoring.op_or_opequal_usage"
    description = (
        "Refactor between `x <op>= y` and `x = x <op> y` styles "
        "for + - * / operators."
    )
    # Official variant names exposed to the CLI / config layer.
    variants = ("opequal", "op_assign")

    def _target_form_for(
        self, current: OpOrOpEqualUsageForm
    ) -> Optional[OpOrOpEqualUsageForm]:
        """
        Determine the target form from the current form and RuleDirection.
        Return None when no rewrite is needed.
        """
        direction = self.direction

        if direction.mode == "AUTO":
            # AUTO: toggle between the two forms.
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

        # No rewrite is needed if the target already matches the current form.
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
