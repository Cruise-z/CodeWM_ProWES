# pyCodeObfuscator/patterns/AL/expression/boolean_explicit_true_false_pattern.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import libcst as cst


class BooleanExplicitForm(str, Enum):
    """
    Two forms:

    - EXPLICIT_TRUE_FALSE:
        True if b_expr else False

    - DIRECT_EXPR:
        A clearly boolean expression b_expr (comparison, boolean operation,
        not, etc.)
    """
    EXPLICIT_TRUE_FALSE = "explicit_true_false"
    DIRECT_EXPR = "direct_expr"


@dataclass
class BooleanExplicitTrueFalseMatch:
    """
    Match information for one explicit True/False boolean rule occurrence.
    """
    form: BooleanExplicitForm
    value: cst.BaseExpression        # The entire RHS expression
    inner_expr: cst.BaseExpression   # The b_expression itself, used for rewriting


def _is_true_name(expr: cst.BaseExpression) -> bool:
    return isinstance(expr, cst.Name) and expr.value == "True"


def _is_false_name(expr: cst.BaseExpression) -> bool:
    return isinstance(expr, cst.Name) and expr.value == "False"


def _looks_like_boolean_expr(expr: cst.BaseExpression) -> bool:
    """
    Heuristically determine whether an expression is clearly boolean.

    Only accepts:
        - Comparison expressions: a > 0, x == y, x in y, x is y ...
        - Boolean operations: a > 0 and b < 5, x or y
        - not operations: not x

    Literals such as 0, 1, 2, "str", or a plain variable name are not treated
    as boolean expressions.

    For compatibility with older libcst versions, this does not rely on
    ParenthesizedExpression; that is, if you write
    (a > 0 and b < 5), the inner node is still usually a
    BooleanOperation/Comparison, so this check still works.
    """
    # a > 0, x == y, x in y, ...
    if isinstance(expr, cst.Comparison):
        return True

    # a and b, a or b
    if isinstance(expr, cst.BooleanOperation):
        return True

    # not x
    if isinstance(expr, cst.UnaryOperation) and isinstance(expr.operator, cst.Not):
        return True

    return False

def match_boolean_explicit_true_false(
    expr: cst.BaseExpression,
) -> Optional[BooleanExplicitTrueFalseMatch]:
    """
    Try to match one of the following forms on an expression:

    1) EXPLICIT_TRUE_FALSE form:
        True if b_expr else False

    2) DIRECT_EXPR form:
        A clearly boolean b_expr (comparison, boolean operation, not, etc.)

    Other cases (such as z = 0, x = 2, s = "abc", etc.) do not match and
    return None.
    """

    # Form 1: True if b_expr else False
    if isinstance(expr, cst.IfExp) and _is_true_name(expr.body) and _is_false_name(
        expr.orelse
    ):
        return BooleanExplicitTrueFalseMatch(
            form=BooleanExplicitForm.EXPLICIT_TRUE_FALSE,
            value=expr,
            inner_expr=expr.test,
        )

    # Form 2: a clearly boolean expression
    if _looks_like_boolean_expr(expr):
        return BooleanExplicitTrueFalseMatch(
            form=BooleanExplicitForm.DIRECT_EXPR,
            value=expr,
            inner_expr=expr,
        )

    # Other cases are not considered matches for this rule.
    return None
