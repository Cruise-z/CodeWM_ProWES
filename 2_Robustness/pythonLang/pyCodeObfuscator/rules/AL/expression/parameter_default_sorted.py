# pyCodeObfuscator/rules/AL/expression/parameter_default_sorted.py
from __future__ import annotations

from typing import Optional, List

import libcst as cst

from pyCodeObfuscator.core.rule_base import BaseRule, RuleDirection, register_rule
from pyCodeObfuscator.patterns.AL.expression.parameter_default_sorted_pattern import (
    ParameterDefaultSortedForm,
    ParameterDefaultSortedMatch,
    match_parameter_default_sorted,
)


@register_rule
class ParameterDefaultSortedRule(BaseRule):
    """
    统一/互转：
      - sorted(arr) / sorted(arr, key=...)      （不显式写 reverse）
      - sorted(arr, reverse=False) / ...        （显式 reverse=False）
    """

    rule_id = "refactoring.parameter_default_sorted"
    description = "Normalize usage of sorted(..., reverse=False) vs sorted(...)"
    variants = ("explicit_reverse_false", "no_reverse")

    _VARIANT_KEY_TO_FORM: dict[str, ParameterDefaultSortedForm] = {
        # 显式 reverse=False
        "explicit_reverse_false": ParameterDefaultSortedForm.EXPLICIT_REVERSE_FALSE,
        "explicit": ParameterDefaultSortedForm.EXPLICIT_REVERSE_FALSE,
        "reverse_false": ParameterDefaultSortedForm.EXPLICIT_REVERSE_FALSE,
        # 不写 reverse 参数
        "no_reverse": ParameterDefaultSortedForm.NO_REVERSE,
        "implicit": ParameterDefaultSortedForm.NO_REVERSE,
    }

    def _target_form_for(
        self, current: ParameterDefaultSortedForm
    ) -> Optional[ParameterDefaultSortedForm]:
        direction = self.direction

        # AUTO 模式：两种形态互相翻转
        if direction.mode == "AUTO":
            if current is ParameterDefaultSortedForm.NO_REVERSE:
                return ParameterDefaultSortedForm.EXPLICIT_REVERSE_FALSE
            if current is ParameterDefaultSortedForm.EXPLICIT_REVERSE_FALSE:
                return ParameterDefaultSortedForm.NO_REVERSE
            return None

        # 指定形态模式
        if direction.mode == "TO_VARIANT":
            key = direction.variant
            if key is None:
                return None
            form = self._VARIANT_KEY_TO_FORM.get(key.lower())
            if form is None or form is current:
                return None
            return form

        return None

    # 表达式级规则，直接挂在 Call 上
    def leave_Call(
        self, original_node: cst.Call, updated_node: cst.Call
    ) -> cst.BaseExpression:
        match = match_parameter_default_sorted(updated_node)
        if match is None:
            return updated_node

        target_form = self._target_form_for(match.form)
        if target_form is None:
            return updated_node

        if (
            match.form is ParameterDefaultSortedForm.NO_REVERSE
            and target_form is ParameterDefaultSortedForm.EXPLICIT_REVERSE_FALSE
        ):
            return _rewrite_no_reverse_to_explicit(match)

        if (
            match.form is ParameterDefaultSortedForm.EXPLICIT_REVERSE_FALSE
            and target_form is ParameterDefaultSortedForm.NO_REVERSE
        ):
            return _rewrite_explicit_to_no_reverse(match)

        return updated_node


# ---- 具体改写逻辑 -----------------------------------------------------------------


def _build_reverse_false_arg() -> cst.Arg:
    """
    构造一个 keyword 参数：reverse=False
    注意：这里显式使用 AssignEqual 并把前后空白设为 ""，
    这样生成的代码就是 `reverse=False` 而不是 `reverse = False`。
    """
    return cst.Arg(
        value=cst.Name("False"),
        keyword=cst.Name("reverse"),
        equal=cst.AssignEqual(
            whitespace_before=cst.SimpleWhitespace(""),
            whitespace_after=cst.SimpleWhitespace(""),
        ),
        # 其它字段用默认即可：
        # comma=MaybeSentinel.DEFAULT, star="", whitespace_after_star="", whitespace_after_arg=""
    )


def _rewrite_no_reverse_to_explicit(
    match: ParameterDefaultSortedMatch,
) -> cst.Call:
    """
    sorted(arr) / sorted(arr, key=...)  ->  在参数列表末尾增加 reverse=False
    """
    call = match.call
    reverse_arg = _build_reverse_false_arg()

    # 直接在现有参数列表后面 append 一个新的 Arg
    new_args: List[cst.Arg] = [*call.args, reverse_arg]
    return call.with_changes(args=new_args)


def _rewrite_explicit_to_no_reverse(
    match: ParameterDefaultSortedMatch,
) -> cst.Call:
    """
    sorted(arr, ..., reverse=False)  ->  删除 reverse=False，并去掉多余逗号

    这里要特别处理：
      - 原先 `reverse=False` 前面的那个参数通常带着逗号；
      - 删除 reverse 参数后，如果不清理逗号，就会得到 `sorted(arr, )`
    """
    call = match.call
    reverse_arg = match.reverse_arg
    if reverse_arg is None:
        return call

    # 去掉 reverse=False 这个 Arg
    new_args: List[cst.Arg] = []
    for arg in call.args:
        if arg is reverse_arg:
            continue
        new_args.append(arg)

    # 如果删完一个参数后没有任何参数了，直接给一个空列表即可
    if not new_args:
        return call.with_changes(args=())

    # 把“最后一个参数”的 comma 统一重置为 MaybeSentinel.DEFAULT，
    # 这样 Call._codegen_impl 会认为它是最后一个参数，不再强制输出逗号。
    last = new_args[-1].with_changes(comma=cst.MaybeSentinel.DEFAULT)
    new_args[-1] = last

    return call.with_changes(args=new_args)
