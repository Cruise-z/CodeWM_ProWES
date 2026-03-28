# pyCodeObfuscator/rules/AL/expression/boolean_explicit_true_false.py
from __future__ import annotations

import libcst as cst

from ....core.rule_base import BaseRule, RuleDirection, register_rule
from ....patterns.AL.expression.boolean_explicit_true_false_pattern import (
    match_boolean_explicit_true_false,
    BooleanExplicitForm,
    BooleanExplicitTrueFalseMatch,
)


# Map variant strings to forms:
#   - "explicit" / "true_false" / "ternary"   -> EXPLICIT_TRUE_FALSE
#   - "direct" / "expr" / "boolean_expr"      -> DIRECT_EXPR
_VARIANT_KEY_TO_FORM: dict[str, BooleanExplicitForm] = {
    "explicit": BooleanExplicitForm.EXPLICIT_TRUE_FALSE,
    "true_false": BooleanExplicitForm.EXPLICIT_TRUE_FALSE,
    "ternary": BooleanExplicitForm.EXPLICIT_TRUE_FALSE,
    "explicit_true_false": BooleanExplicitForm.EXPLICIT_TRUE_FALSE,

    "direct": BooleanExplicitForm.DIRECT_EXPR,
    "expr": BooleanExplicitForm.DIRECT_EXPR,
    "boolean": BooleanExplicitForm.DIRECT_EXPR,
    "boolean_expr": BooleanExplicitForm.DIRECT_EXPR,
}


def _wrap_as_explicit_true_false(match: BooleanExplicitTrueFalseMatch) -> cst.IfExp:
    """
    Based on the match result, wrap inner_expr as:
        True if inner_expr else False
    """
    return cst.IfExp(
        test=match.inner_expr,
        body=cst.Name("True"),
        orelse=cst.Name("False"),
    )


@register_rule
class BooleanExplicitTrueFalseRule(BaseRule):
    """
    Multi-variant rule:

    Form A: EXPLICIT_TRUE_FALSE
        var = True if b_expression else False

    Form B: DIRECT_EXPR
        var = b_expression

    Direction rules, based on the new RuleDirection:

      - direction.mode == "AUTO":
            EXPLICIT_TRUE_FALSE  -> DIRECT_EXPR
            DIRECT_EXPR          -> EXPLICIT_TRUE_FALSE

      - direction.mode == "TO_VARIANT":
            direction.variant is a string key:
                "explicit" / "true_false" / "ternary" / ...
                "direct" / "expr" / "boolean_expr" / ...
            This rule maps those keys to BooleanExplicitForm and converts between the two forms accordingly.
    """

    rule_id = "refactoring.boolean_explicit_true_false"
    description = "True if b_expr else False <-> b_expr"
    variants = ("explicit", "direct")

    # ------- Determine the target form from direction -------

    def _target_form_for(
        self,
        match: BooleanExplicitTrueFalseMatch,
    ) -> BooleanExplicitForm | None:
        cur = match.form
        direction = self.direction

        # AUTO: swap between the two forms
        if direction.mode == "AUTO":
            if cur is BooleanExplicitForm.EXPLICIT_TRUE_FALSE:
                target = BooleanExplicitForm.DIRECT_EXPR
            elif cur is BooleanExplicitForm.DIRECT_EXPR:
                target = BooleanExplicitForm.EXPLICIT_TRUE_FALSE
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
        if target is cur:
            return None

        return target

    # ------- Main rewrite logic: rewrite the RHS of assignments -------

    def leave_Assign(
        self,
        original_node: cst.Assign,
        updated_node: cst.Assign,
    ) -> cst.Assign:
        value = updated_node.value

        match = match_boolean_explicit_true_false(value)
        # No form of this rule matched, so return directly
        if match is None:
            return updated_node

        target_form = self._target_form_for(match)
        if target_form is None:
            return updated_node

        # ---------- EXPLICIT_TRUE_FALSE -> DIRECT_EXPR ----------
        # var = True if b_expr else False  ->  var = b_expr
        if (
            match.form is BooleanExplicitForm.EXPLICIT_TRUE_FALSE
            and target_form is BooleanExplicitForm.DIRECT_EXPR
        ):
            return updated_node.with_changes(value=match.inner_expr)

        # ---------- DIRECT_EXPR -> EXPLICIT_TRUE_FALSE ----------
        # var = b_expr  ->  var = True if b_expr else False
        if (
            match.form is BooleanExplicitForm.DIRECT_EXPR
            and target_form is BooleanExplicitForm.EXPLICIT_TRUE_FALSE
        ):
            # Only handle simple single-target assignments: var = ...
            if len(updated_node.targets) != 1:
                return updated_node
            target = updated_node.targets[0].target
            if not isinstance(target, cst.Name):
                return updated_node

            new_value = _wrap_as_explicit_true_false(match)
            return updated_node.with_changes(value=new_value)

        # Fallback: do not rewrite
        return updated_node
