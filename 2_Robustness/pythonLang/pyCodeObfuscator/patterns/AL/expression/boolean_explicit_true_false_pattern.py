# pyCodeObfuscator/patterns/AL/expression/boolean_explicit_true_false_pattern.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import libcst as cst


class BooleanExplicitForm(str, Enum):
    """
    两种形态：

    - EXPLICIT_TRUE_FALSE:
        True if b_expr else False

    - DIRECT_EXPR:
        明显的布尔表达式 b_expr（比较、逻辑运算、not 等）
    """
    EXPLICIT_TRUE_FALSE = "explicit_true_false"
    DIRECT_EXPR = "direct_expr"


@dataclass
class BooleanExplicitTrueFalseMatch:
    """
    布尔显式 True/False 规则的一次命中信息。
    """
    form: BooleanExplicitForm
    value: cst.BaseExpression        # 整个 RHS 表达式
    inner_expr: cst.BaseExpression   # b_expression 本体（用于转换）


def _is_true_name(expr: cst.BaseExpression) -> bool:
    return isinstance(expr, cst.Name) and expr.value == "True"


def _is_false_name(expr: cst.BaseExpression) -> bool:
    return isinstance(expr, cst.Name) and expr.value == "False"


def _looks_like_boolean_expr(expr: cst.BaseExpression) -> bool:
    """
    粗略判断一个表达式是否“明显是布尔表达式”。

    我们只接受：
        - 比较表达式: a > 0, x == y, x in y, x is y ...
        - 逻辑运算: a > 0 and b < 5, x or y
        - not 运算: not x

    像 0、1、2、"str"、普通变量名等都不会被视为布尔表达式。

    为了兼容旧版本 libcst，这里不依赖 ParenthesizedExpression；
    也就是说，如果你写了 (a > 0 and b < 5)，内部通常仍然是 BooleanOperation/Comparison，
    这个判断仍然成立。
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
    尝试在一个表达式上匹配：

    1) EXPLICIT_TRUE_FALSE 形态：
        True if b_expr else False

    2) DIRECT_EXPR 形态：
        明显是布尔表达式的 b_expr（比较、逻辑运算、not 等）

    其它情况（如 z = 0, x = 2, s = "abc" 等）不匹配，返回 None。
    """

    # 形态 1：True if b_expr else False
    if isinstance(expr, cst.IfExp) and _is_true_name(expr.body) and _is_false_name(
        expr.orelse
    ):
        return BooleanExplicitTrueFalseMatch(
            form=BooleanExplicitForm.EXPLICIT_TRUE_FALSE,
            value=expr,
            inner_expr=expr.test,
        )

    # 形态 2：明显的布尔表达式
    if _looks_like_boolean_expr(expr):
        return BooleanExplicitTrueFalseMatch(
            form=BooleanExplicitForm.DIRECT_EXPR,
            value=expr,
            inner_expr=expr,
        )

    # 其他情况不认为是这条规则的匹配
    return None
