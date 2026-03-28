# pyCodeObfuscator/rules/AL/expression/none_usage.py
from __future__ import annotations

from typing import Optional, Sequence

import libcst as cst

from ....core.rule_base import BaseRule, RuleDirection, register_rule
from ....patterns.AL.expression.none_usage_pattern import (
    match_none_usage,
    NoneUsageForm,
    NoneUsageMatch,
)


def _build_is_not_none_expr(match: NoneUsageMatch) -> cst.Comparison:
    """
    x  ->  x is not None
    """
    comp = cst.Comparison(
        left=match.var_expr,
        comparisons=[
            cst.ComparisonTarget(
                operator=cst.IsNot(),
                comparator=cst.Name("None"),
            )
        ],
    )

    # Preserve the outer parentheses of the original expression when present
    lpar: Sequence[cst.LeftParen] = getattr(match.expr, "lpar", ())
    rpar: Sequence[cst.RightParen] = getattr(match.expr, "rpar", ())

    if lpar or rpar:
        comp = comp.with_changes(lpar=list(lpar), rpar=list(rpar))

    return comp


def _build_bare_expr(match: NoneUsageMatch) -> cst.BaseExpression:
    """
    x is not None  ->  x
    """
    new_expr = match.var_expr

    # Also preserve the outer parentheses of the original comparison expression when possible
    lpar: Sequence[cst.LeftParen] = getattr(match.expr, "lpar", ())
    rpar: Sequence[cst.RightParen] = getattr(match.expr, "rpar", ())

    if lpar or rpar:
        new_expr = new_expr.with_changes(lpar=list(lpar), rpar=list(rpar))

    return new_expr


# Map variant strings to target forms:
#   - "bare"/"truthy"          -> BARE_TRUTHY
#   - "is_not_none"/"explicit" -> IS_NOT_NONE
_VARIANT_KEY_TO_FORM: dict[str, NoneUsageForm] = {
    "bare":        NoneUsageForm.BARE_TRUTHY,
    "truthy":      NoneUsageForm.BARE_TRUTHY,
    "bare_truthy": NoneUsageForm.BARE_TRUTHY,

    "is_not_none": NoneUsageForm.IS_NOT_NONE,
    "explicit":    NoneUsageForm.IS_NOT_NONE,
}


@register_rule
class NoneUsageRule(BaseRule):
    """
    Two common styles for using None in conditions:

        if x:
            ...

        if x is not None:
            ...

    Multi-variant direction rules (based on the new RuleDirection):

      - direction.mode == "AUTO":
            BARE_TRUTHY  -> IS_NOT_NONE
            IS_NOT_NONE  -> BARE_TRUTHY

      - direction.mode == "TO_VARIANT":
            direction.variant is a string key:
                "bare" / "truthy" / "bare_truthy"
                "is_not_none" / "explicit"
            This rule maps those keys to NoneUsageForm and performs the corresponding conversion between the two forms.
    """

    rule_id = "refactoring.none_usage"
    description = "Use of None in conditions: x <-> x is not None"
    variants = ("bare", "is_not_none")

    # ------- Determine the target form from direction -------

    def _target_form_for(self, current: NoneUsageForm) -> Optional[NoneUsageForm]:
        direction = self.direction

        # AUTO: swap between the two forms
        if direction.mode == "AUTO":
            if current is NoneUsageForm.BARE_TRUTHY:
                target = NoneUsageForm.IS_NOT_NONE
            elif current is NoneUsageForm.IS_NOT_NONE:
                target = NoneUsageForm.BARE_TRUTHY
            else:
                return None

        # TO_VARIANT: determine the target form from the variant string
        elif direction.mode == "TO_VARIANT":
            key = direction.variant
            if key is None:
                return None
            form = _VARIANT_KEY_TO_FORM.get(key.lower())
            if form is None:
                # Unknown key: do not rewrite
                return None
            target = form

        else:
            # Unknown mode: do not rewrite
            return None

        # Do not rewrite if the current form already matches the target
        if target is current:
            return None

        return target

    # Unified rewrite logic: check whether a conditional expression should be rewritten
    def _rewrite_cond_expr(
        self,
        test_expr: cst.BaseExpression,
    ) -> Optional[cst.BaseExpression]:
        match = match_none_usage(test_expr)
        if match is None:
            return None

        target_form = self._target_form_for(match.form)
        if target_form is None:
            return None

        # BARE_TRUTHY -> IS_NOT_NONE
        if (
            match.form is NoneUsageForm.BARE_TRUTHY
            and target_form is NoneUsageForm.IS_NOT_NONE
        ):
            return _build_is_not_none_expr(match)

        # IS_NOT_NONE -> BARE_TRUTHY
        if (
            match.form is NoneUsageForm.IS_NOT_NONE
            and target_form is NoneUsageForm.BARE_TRUTHY
        ):
            return _build_bare_expr(match)

        return None

    # ------------ Attach the rewrite to concrete syntax nodes ------------

    def leave_If(self, original_node: cst.If, updated_node: cst.If) -> cst.If:
        new_test = self._rewrite_cond_expr(updated_node.test)
        if new_test is None:
            return updated_node
        return updated_node.with_changes(test=new_test)

    def leave_While(
        self,
        original_node: cst.While,
        updated_node: cst.While,
    ) -> cst.While:
        new_test = self._rewrite_cond_expr(updated_node.test)
        if new_test is None:
            return updated_node
        return updated_node.with_changes(test=new_test)

    def leave_Assert(
        self,
        original_node: cst.Assert,
        updated_node: cst.Assert,
    ) -> cst.Assert:
        new_test = self._rewrite_cond_expr(updated_node.test)
        if new_test is None:
            return updated_node
        return updated_node.with_changes(test=new_test)

    def leave_IfExp(
        self,
        original_node: cst.IfExp,
        updated_node: cst.IfExp,
    ) -> cst.IfExp:
        new_test = self._rewrite_cond_expr(updated_node.test)
        if new_test is None:
            return updated_node
        return updated_node.with_changes(test=new_test)

    def leave_CompIf(
        self,
        original_node: cst.CompIf,
        updated_node: cst.CompIf,
    ) -> cst.CompIf:
        new_test = self._rewrite_cond_expr(updated_node.test)
        if new_test is None:
            return up
