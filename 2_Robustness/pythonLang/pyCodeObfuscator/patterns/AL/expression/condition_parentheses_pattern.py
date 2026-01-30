# pyCodeObfuscator/patterns/AL/expression/condition_parentheses_pattern.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import libcst as cst


class ConditionParensForm(str, Enum):
    """
    条件表达式的两种形态：
    - NO_PARENS  : userid == 0
    - HAS_PARENS : (userid == 0)
    """
    NO_PARENS = "no_parens"
    HAS_PARENS = "has_parens"


@dataclass
class ConditionParenthesesMatch:
    """
    条件括号使用的一次命中信息。
    """
    form: ConditionParensForm
    expr: cst.BaseExpression  # if/while 的 test 表达式本身


def _looks_like_boolean_condition(expr: cst.BaseExpression) -> bool:
    """
    粗略判断是否是一个“典型布尔条件表达式”，避免对 z = 0 这类乱动。

    这里只接受：
        - 比较表达式: a > 0, x == y, x in y, x is y, ...
        - 逻辑运算: a > 0 and b < 5, x or y
        - not 运算: not x
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
    在一个表达式上尝试匹配“条件括号使用”模式。

    - 如果不是典型布尔条件表达式，则不认为是本规则的命中，返回 None；
    - 否则，根据是否存在外层括号，返回 HAS_PARENS / NO_PARENS。
    """
    if not _looks_like_boolean_condition(expr):
        return None

    # 大部分表达式节点都有 lpar / rpar 字段，表示外层括号。
    lpar = getattr(expr, "lpar", ())
    rpar = getattr(expr, "rpar", ())

    has_parens = bool(lpar) or bool(rpar)
    form = ConditionParensForm.HAS_PARENS if has_parens else ConditionParensForm.NO_PARENS

    return ConditionParenthesesMatch(
        form=form,
        expr=expr,
    )
