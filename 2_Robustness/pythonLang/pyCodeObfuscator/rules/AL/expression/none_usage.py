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

    # 保留原表达式的外层括号（如果有）
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

    # 也尽量保留原比较表达式的外层括号
    lpar: Sequence[cst.LeftParen] = getattr(match.expr, "lpar", ())
    rpar: Sequence[cst.RightParen] = getattr(match.expr, "rpar", ())

    if lpar or rpar:
        new_expr = new_expr.with_changes(lpar=list(lpar), rpar=list(rpar))

    return new_expr


# 将 variant 字符串映射到目标形态：
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
    条件中使用 None 的两种习惯写法：

        if x:
            ...

        if x is not None:
            ...

    多形态方向约定（基于新的 RuleDirection）：

      - direction.mode == "AUTO":
            BARE_TRUTHY  -> IS_NOT_NONE
            IS_NOT_NONE  -> BARE_TRUTHY

      - direction.mode == "TO_VARIANT":
            direction.variant 为字符串 key：
                "bare" / "truthy" / "bare_truthy"
                "is_not_none" / "explicit"
            本规则将这些 key 映射到 NoneUsageForm，并在两种形态之间做对应转换。
    """

    rule_id = "refactoring.none_usage"
    description = "条件中使用 None 关键字：x <-> x is not None"
    variants = ("bare", "is_not_none")

    # ------- 根据 direction 决定目标形态 -------

    def _target_form_for(self, current: NoneUsageForm) -> Optional[NoneUsageForm]:
        direction = self.direction

        # AUTO：两种形态互换
        if direction.mode == "AUTO":
            if current is NoneUsageForm.BARE_TRUTHY:
                target = NoneUsageForm.IS_NOT_NONE
            elif current is NoneUsageForm.IS_NOT_NONE:
                target = NoneUsageForm.BARE_TRUTHY
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

        # 当前形态已经是目标形态则不改写
        if target is current:
            return None

        return target

    # 统一改写逻辑：给一个条件表达式，看看要不要改
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

    # ------------ 挂到具体语法节点上 ------------

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
