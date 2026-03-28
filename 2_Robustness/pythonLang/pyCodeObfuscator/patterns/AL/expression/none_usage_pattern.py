# pyCodeObfuscator/patterns/AL/expression/none_usage_pattern.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import libcst as cst


class NoneUsageForm(str, Enum):
    """
    Two forms:
    - BARE_TRUTHY : if x:
    - IS_NOT_NONE : if x is not None:
    """
    BARE_TRUTHY = "bare_truthy"
    IS_NOT_NONE = "is_not_none"


@dataclass
class NoneUsageMatch:
    """
    Match information for one occurrence of 'x' <-> 'x is not None'.
    """
    form: NoneUsageForm
    expr: cst.BaseExpression        # Entire conditional expression, possibly with parentheses
    var_expr: cst.BaseExpression    # Variable expression x or obj.x


def _match_is_not_none(expr: cst.BaseExpression) -> Optional[NoneUsageMatch]:
    """
    Match the form 'x is not None'.
    """
    if not isinstance(expr, cst.Comparison):
        return None
    if len(expr.comparisons) != 1:
        return None

    target = expr.comparisons[0]

    # Operator must be "is not"
    if not isinstance(target.operator, cst.IsNot):
        return None

    # Right side must be None
    comparator = target.comparator
    if not isinstance(comparator, cst.Name) or comparator.value != "None":
        return None

    # Left-side variable: Name or Attribute (x / obj.x)
    left = expr.left
    if not isinstance(left, (cst.Name, cst.Attribute)):
        return None

    return NoneUsageMatch(
        form=NoneUsageForm.IS_NOT_NONE,
        expr=expr,
        var_expr=left,
    )


def _match_bare_truthy(expr: cst.BaseExpression) -> Optional[NoneUsageMatch]:
    """
    Match bare-variable conditions: if x: / if obj.x:
    This avoids treating complex expressions or literals as this rule.
    """
    if isinstance(expr, (cst.Name, cst.Attribute)):
        # Exclude literal names such as None / True / False
        if isinstance(expr, cst.Name) and expr.value in ("None", "True", "False"):
            return None

        return NoneUsageMatch(
            form=NoneUsageForm.BARE_TRUTHY,
            expr=expr,
            var_expr=expr,
        )
    return None


def match_none_usage(
    expr: cst.BaseExpression,
) -> Optional[NoneUsageMatch]:
    """
    Try to match on an expression:

      - x
      - x is not None

    Return NoneUsageMatch on success, otherwise return None.
    """
    # Check the more specific is-not-None form first
    m = _match_is_not_none(expr)
    if m is not None:
        return m

    return _match_bare_truthy(expr)
