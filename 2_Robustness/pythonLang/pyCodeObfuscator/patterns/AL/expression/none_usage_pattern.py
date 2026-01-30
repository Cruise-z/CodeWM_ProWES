# pyCodeObfuscator/patterns/AL/expression/none_usage_pattern.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import libcst as cst


class NoneUsageForm(str, Enum):
    """
    两种形态：
    - BARE_TRUTHY : if x:
    - IS_NOT_NONE : if x is not None:
    """
    BARE_TRUTHY = "bare_truthy"
    IS_NOT_NONE = "is_not_none"


@dataclass
class NoneUsageMatch:
    """
    'x' <-> 'x is not None' 的一次命中信息。
    """
    form: NoneUsageForm
    expr: cst.BaseExpression        # 整个条件表达式（可能带括号）
    var_expr: cst.BaseExpression    # 变量表达式 x 或 obj.x


def _match_is_not_none(expr: cst.BaseExpression) -> Optional[NoneUsageMatch]:
    """
    匹配 'x is not None' 形式。
    """
    if not isinstance(expr, cst.Comparison):
        return None
    if len(expr.comparisons) != 1:
        return None

    target = expr.comparisons[0]

    # operator 必须是 "is not"
    if not isinstance(target.operator, cst.IsNot):
        return None

    # 右侧必须是 None
    comparator = target.comparator
    if not isinstance(comparator, cst.Name) or comparator.value != "None":
        return None

    # 左侧变量：Name 或 Attribute（x / obj.x）
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
    匹配裸变量条件：if x: / if obj.x:
    （避免把复杂表达式、字面量当成这个规则。）
    """
    if isinstance(expr, (cst.Name, cst.Attribute)):
        # 排除 None / True / False 这些字面量名
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
    在一个表达式上尝试匹配：

      - x
      - x is not None

    命中返回 NoneUsageMatch，否则返回 None。
    """
    # 更具体的 is-not-None 先判
    m = _match_is_not_none(expr)
    if m is not None:
        return m

    return _match_bare_truthy(expr)
