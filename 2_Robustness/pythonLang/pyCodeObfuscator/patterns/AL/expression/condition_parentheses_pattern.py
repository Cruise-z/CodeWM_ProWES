# pyCodeObfuscator/patterns/AL/expression/condition_parentheses_pattern.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import libcst as cst


class ConditionParensForm(str, Enum):
    """
    Two forms of a conditional expression:
    - NO_PARENS  : userid == 0
    - HAS_PARENS : (userid == 0)
    """
    NO_PARENS = "no_parens"
    HAS_PARENS = "has_parens"


@dataclass
class ConditionParenthesesMatch:
    """
    Match information for one condition-parentheses occurrence.
    """
    form: ConditionParensForm
    expr: cst.BaseExpression  # The if/while test expression itself


def _looks_like_boolean_condition(expr: cst.BaseExpression) -> bool:
    """
    Heuristically determine whether this looks like a typical boolean
    condition expression, to avoid rewriting unrelated expressions such as
    z = 0.

    Only accepts:
        - Comparison expressions: a > 0, x == y, x in y, x is y, ...
        - Boolean operations: a > 0 and b < 5, x or y
        - not operations: not x
    """
    if isinstance(expr, cst.Comparison):
        return True
    if isinstance(expr, cst.BooleanOperation):
        return True
    if isinstance(expr, cst.UnaryOperation) and isinstance(expr.operator, cst.Not):
        return True
    return False


def match_condition_parentheses(
    expr: cst.BaseExpression,
) -> Optional[ConditionParenthesesMatch]:
    """
    Try to match the "condition parentheses usage" pattern on an expression.

    - If it is not a typical boolean condition expression, this rule does not
      treat it as a match and returns None.
    - Otherwise, return HAS_PARENS / NO_PARENS based on whether outer
      parentheses are present.
    """
    if not _looks_like_boolean_condition(expr):
        return None

    # Most expression nodes have lpar / rpar fields representing outer
    # parentheses.
    lpar = getattr(expr, "lpar", ())
    rpar = getattr(expr, "rpar", ())

    has_parens = bool(lpar) or bool(rpar)
    form = ConditionParensForm.HAS_PARENS if has_parens else ConditionParensForm.NO_PARENS

    return ConditionParenthesesMatch(
        form=form,
        expr=expr,
    )
