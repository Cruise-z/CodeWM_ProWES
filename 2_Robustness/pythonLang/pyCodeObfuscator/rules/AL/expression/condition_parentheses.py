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
    从表达式上去掉一层外层括号（如果有）。
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
    在表达式外侧再包一层括号。
    """
    lpar: Sequence[cst.LeftParen] = getattr(expr, "lpar", ())
    rpar: Sequence[cst.RightParen] = getattr(expr, "rpar", ())

    new_lpar = list(lpar)
    new_rpar = list(rpar)

    new_lpar.append(cst.LeftParen())
    new_rpar.append(cst.RightParen())

    return expr.with_changes(lpar=new_lpar, rpar=new_rpar)


# 将 variant 字符串映射到目标形态：
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
    条件括号使用规则，当前作用于这些位置：

      - if <cond>:
      - while <cond>:
      - assert <cond>
      - <a> if <cond> else <b>   （三元表达式）
      - 推导式中的 if <cond>：
            [x for x in xs if <cond>]
            {x for x in xs if <cond>}
            (x for x in xs if <cond>)
            {k: v for k, v in xs if <cond>}

    多形态方向约定（基于新的 RuleDirection）：

      - direction.mode == "AUTO":
            HAS_PARENS  -> NO_PARENS
            NO_PARENS   -> HAS_PARENS

      - direction.mode == "TO_VARIANT":
            direction.variant 为字符串 key：
                "no_parens" / "bare" / "minimal"
                "parens" / "with_parens" / "wrapped"
            本规则将这些 key 映射到 ConditionParensForm，并在两种形态之间做对应转换。
    """

    rule_id = "refactoring.condition_parentheses_usage"
    description = "条件表达式外层括号的使用（if/while/assert/ifexp/comprehension）"

    # 声明本规则支持的变体名称（用于 CLI/文档）
    variants = ("no_parens", "parens")

    # ----------------- 公共决策逻辑：当前形态 -> 目标形态 -----------------

    def _target_form_for(
        self,
        current: ConditionParensForm,
    ) -> Optional[ConditionParensForm]:
        direction = self.direction

        # AUTO：两种形态互换
        if direction.mode == "AUTO":
            if current is ConditionParensForm.HAS_PARENS:
                target = ConditionParensForm.NO_PARENS
            elif current is ConditionParensForm.NO_PARENS:
                target = ConditionParensForm.HAS_PARENS
            else:
                return None

        # TO_VARIANT：根据 variant 字符串决定目标形态
        elif direction.mode == "TO_VARIANT":
            key = direction.variant
            if key is None:
                return None
            form = _VARIANT_KEY_TO_FORM.get(key.lower())
            if form is None:
                # 不认识的 key：不改写
                return None
            target = form

        else:
            # 未知 mode：不改写
            return None

        # 如果当前形态已经是目标形态，则不改写
        if target is current:
            return None

        return target

    # ----------------- 公共表达式改写逻辑 -----------------

    def _rewrite_test_expr(
        self,
        test_expr: cst.BaseExpression,
    ) -> Optional[cst.BaseExpression]:
        """
        对条件表达式应用括号规则：
          - HAS_PARENS -> NO_PARENS：去掉一层括号
          - NO_PARENS  -> HAS_PARENS：加一层括号
        具体由 RuleDirection 决定是否以及朝哪个方向改写。
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

    # ----------------- 具体语法节点 -----------------

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
        推导式中的 if <cond> 子句：
            [x for x in xs if <cond>]
        """
        new_test = self._rewrite_test_expr(updated_node.test)
        if new_test is None:
            return updated_node
        return updated_node.with_changes(test=new_test)
