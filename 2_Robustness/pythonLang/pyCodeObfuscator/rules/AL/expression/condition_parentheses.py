# pyCodeObfuscator/rules/AL/expression/condition_parentheses.py
from __future__ import annotations

from typing import Sequence, Optional

import libcst as cst

from ....core.rule_base import BaseRule, RuleDirection, register_rule
from ....patterns.AL.expression.condition_parentheses_pattern import (
    match_condition_parentheses,
    ConditionParensForm,
    ConditionParenthesesMatch,
)


def _remove_outer_parens(expr: cst.BaseExpression) -> cst.BaseExpression:
    """
    Remove one layer of outer parentheses from the expression, if present.
    """
    lpar: Sequence[cst.LeftParen] = getattr(expr, "lpar", ())
    rpar: Sequence[cst.RightParen] = getattr(expr, "rpar", ())

    if not lpar and not rpar:
        return expr

    new_lpar = list(lpar)
    new_rpar = list(rpar)

    if new_lpar:
        new_lpar = new_lpar[:-1]
    if new_rpar:
        new_rpar = new_rpar[:-1]

    return expr.with_changes(lpar=new_lpar, rpar=new_rpar)


def _add_outer_parens(expr: cst.BaseExpression) -> cst.BaseExpression:
    """
    Wrap the expression in one additional outer pair of parentheses.
    """
    lpar: Sequence[cst.LeftParen] = getattr(expr, "lpar", ())
    rpar: Sequence[cst.RightParen] = getattr(expr, "rpar", ())

    new_lpar = list(lpar)
    new_rpar = list(rpar)

    new_lpar.append(cst.LeftParen())
    new_rpar.append(cst.RightParen())

    return expr.with_changes(lpar=new_lpar, rpar=new_rpar)


# Map variant strings to target forms:
#   - "no_parens"/"bare"       -> NO_PARENS
#   - "parens"/"with_parens"   -> HAS_PARENS
_VARIANT_KEY_TO_FORM: dict[str, ConditionParensForm] = {
    "no_parens": ConditionParensForm.NO_PARENS,
    "bare": ConditionParensForm.NO_PARENS,
    "minimal": ConditionParensForm.NO_PARENS,

    "parens": ConditionParensForm.HAS_PARENS,
    "with_parens": ConditionParensForm.HAS_PARENS,
    "wrapped": ConditionParensForm.HAS_PARENS,
}


@register_rule
class ConditionParenthesesRule(BaseRule):
    """
    Rule for condition-parentheses usage, currently applied to these positions:

      - if <cond>:
      - while <cond>:
      - assert <cond>
      - <a> if <cond> else <b>   (ternary expression)
      - `if <cond>` inside comprehensions:
            [x for x in xs if <cond>]
            {x for x in xs if <cond>}
            (x for x in xs if <cond>)
            {k: v for k, v in xs if <cond>}

    Multi-variant direction rules (based on the new RuleDirection):

      - direction.mode == "AUTO":
            HAS_PARENS  -> NO_PARENS
            NO_PARENS   -> HAS_PARENS

      - direction.mode == "TO_VARIANT":
            direction.variant is a string key:
                "no_parens" / "bare" / "minimal"
                "parens" / "with_parens" / "wrapped"
            This rule maps those keys to ConditionParensForm and performs the corresponding conversion between the two forms.
    """

    rule_id = "refactoring.condition_parentheses_usage"
    description = "Use of outer parentheses in conditional expressions (if/while/assert/ifexp/comprehension)"

    # Declare the variant names supported by this rule (used for CLI/docs)
    variants = ("no_parens", "parens")

    # ----------------- Shared decision logic: current form -> target form -----------------

    def _target_form_for(
        self,
        current: ConditionParensForm,
    ) -> Optional[ConditionParensForm]:
        direction = self.direction

        # AUTO: swap between the two forms
        if direction.mode == "AUTO":
            if current is ConditionParensForm.HAS_PARENS:
                target = ConditionParensForm.NO_PARENS
            elif current is ConditionParensForm.NO_PARENS:
                target = ConditionParensForm.HAS_PARENS
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

    # ----------------- Shared expression rewrite logic -----------------

    def _rewrite_test_expr(
        self,
        test_expr: cst.BaseExpression,
    ) -> Optional[cst.BaseExpression]:
        """
        Apply the parentheses rule to a conditional expression:
          - HAS_PARENS -> NO_PARENS: remove one layer of parentheses
          - NO_PARENS  -> HAS_PARENS: add one layer of parentheses
        RuleDirection determines whether and in which direction the rewrite occurs.
        """
        match = match_condition_parentheses(test_expr)
        if match is None:
            return None

        target_form = self._target_form_for(match.form)
        if target_form is None:
            return None

        # HAS_PARENS -> NO_PARENS
        if (
            match.form is ConditionParensForm.HAS_PARENS
            and target_form is ConditionParensForm.NO_PARENS
        ):
            return _remove_outer_parens(match.expr)

        # NO_PARENS -> HAS_PARENS
        if (
            match.form is ConditionParensForm.NO_PARENS
            and target_form is ConditionParensForm.HAS_PARENS
        ):
            return _add_outer_parens(match.expr)

        return None

    # ----------------- Concrete syntax nodes -----------------

    def leave_If(self, original_node: cst.If, updated_node: cst.If) -> cst.If:
        new_test = self._rewrite_test_expr(updated_node.test)
        if new_test is None:
            return updated_node
        return updated_node.with_changes(test=new_test)

    def leave_While(
        self,
        original_node: cst.While,
        updated_node: cst.While,
    ) -> cst.While:
        new_test = self._rewrite_test_expr(updated_node.test)
        if new_test is None:
            return updated_node
        return updated_node.with_changes(test=new_test)

    def leave_Assert(
        self,
        original_node: cst.Assert,
        updated_node: cst.Assert,
    ) -> cst.Assert:
        new_test = self._rewrite_test_expr(updated_node.test)
        if new_test is None:
            return updated_node
        return updated_node.with_changes(test=new_test)

    def leave_IfExp(
        self,
        original_node: cst.IfExp,
        updated_node: cst.IfExp,
    ) -> cst.IfExp:
        """
        <a> if <cond> else <b>
        """
        new_test = self._rewrite_test_expr(updated_node.test)
        if new_test is None:
            return updated_node
        return updated_node.with_changes(test=new_test)

    def leave_CompIf(
        self,
        original_node: cst.CompIf,
        updated_node: cst.CompIf,
    ) -> cst.CompIf:
        """
        The `if <cond>` clause inside a comprehension:
            [x for x in xs if <cond>]
        """
        new_test = self._rewrite_test_expr(updated_node.test)
        if new_test is None:
            return updated_node
        return updated_node.with_changes(test=new_test)
