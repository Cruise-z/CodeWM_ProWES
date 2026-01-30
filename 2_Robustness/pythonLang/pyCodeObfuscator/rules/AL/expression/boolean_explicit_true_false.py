# pyCodeObfuscator/rules/AL/expression/boolean_explicit_true_false.py
from __future__ import annotations

import libcst as cst

from ....core.rule_base import BaseRule, RuleDirection, register_rule
from ....patterns.AL.expression.boolean_explicit_true_false_pattern import (
    match_boolean_explicit_true_false,
    BooleanExplicitForm,
    BooleanExplicitTrueFalseMatch,
)


# 将 variant 字符串映射到形态：
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
    根据匹配结果，把 inner_expr 包装成:
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
    多形态规则：

    形态 A：EXPLICIT_TRUE_FALSE
        var = True if b_expression else False

    形态 B：DIRECT_EXPR
        var = b_expression

    方向约定（基于新的 RuleDirection）：

      - direction.mode == "AUTO":
            EXPLICIT_TRUE_FALSE  -> DIRECT_EXPR
            DIRECT_EXPR          -> EXPLICIT_TRUE_FALSE

      - direction.mode == "TO_VARIANT":
            direction.variant 为字符串 key：
                "explicit" / "true_false" / "ternary" / ...
                "direct" / "expr" / "boolean_expr" / ...
            本规则将这些 key 映射到 BooleanExplicitForm，并在两种形态之间做对应转换。
    """

    rule_id = "refactoring.boolean_explicit_true_false"
    description = "True if b_expr else False <-> b_expr"
    variants = ("explicit", "direct")

    # ------- 根据 direction 决定目标形态 -------

    def _target_form_for(
        self,
        match: BooleanExplicitTrueFalseMatch,
    ) -> BooleanExplicitForm | None:
        cur = match.form
        direction = self.direction

        # AUTO：两种形态互换
        if direction.mode == "AUTO":
            if cur is BooleanExplicitForm.EXPLICIT_TRUE_FALSE:
                target = BooleanExplicitForm.DIRECT_EXPR
            elif cur is BooleanExplicitForm.DIRECT_EXPR:
                target = BooleanExplicitForm.EXPLICIT_TRUE_FALSE
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
        if target is cur:
            return None

        return target

    # ------- 主重写逻辑：对赋值 RHS 进行重写 -------

    def leave_Assign(
        self,
        original_node: cst.Assign,
        updated_node: cst.Assign,
    ) -> cst.Assign:
        value = updated_node.value

        match = match_boolean_explicit_true_false(value)
        # 没匹配到这条规则的任何形态，直接返回
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
            # 只处理简单单目标赋值：var = ...
            if len(updated_node.targets) != 1:
                return updated_node
            target = updated_node.targets[0].target
            if not isinstance(target, cst.Name):
                return updated_node

            new_value = _wrap_as_explicit_true_false(match)
            return updated_node.with_changes(value=new_value)

        # 兜底：不改写
        return updated_node
