# pyCodeObfuscator/rules/AL/expression/format_percent_usage.py
from __future__ import annotations

import libcst as cst

from ....core.rule_base import BaseRule, RuleDirection, register_rule
from ....patterns.AL.expression.format_percent_usage_pattern import (
    match_format_percent_usage,
    FormatPercentForm,
    FormatPercentUsageMatch,
    _get_string_inner,
    _replace_string_inner,
)


def _percent_inner_to_format(inner: str) -> str:
    """
    "%s,%s" -> "{},{}"
    （pattern 已保证只存在 %s，没有 %d/%f/%% 等）
    """
    return inner.replace("%s", "{}")


def _format_inner_to_percent(inner: str) -> str:
    """
    "{},{}" / "{0},{1}" -> "%s,%s"

    假设 inner 已经通过 pattern 的 _check_format_template 校验：
      - 只包含 {} 或 {数字}
      - 没有 {{ / }} 等复杂情况
    """
    out_chars: list[str] = []
    i = 0
    n = len(inner)

    while i < n:
        ch = inner[i]
        if ch == "{":
            j = inner.find("}", i + 1)
            if j == -1:
                # 理论上不会发生（pattern 已校验），这里兜个底
                out_chars.append(ch)
                i += 1
            else:
                # 跳过 {...}，统一改成 %s
                out_chars.append("%s")
                i = j + 1
        else:
            out_chars.append(ch)
            i += 1

    return "".join(out_chars)


def _build_format_call(match: FormatPercentUsageMatch) -> cst.Call:
    """
    "%s,%s" % (h, w)  ->  "{},{}".format(h, w)
    """
    inner = _get_string_inner(match.template)
    new_inner = _percent_inner_to_format(inner)
    new_tmpl = _replace_string_inner(match.template, new_inner)

    func = cst.Attribute(
        value=new_tmpl,
        attr=cst.Name("format"),
    )
    args = [cst.Arg(value=a) for a in match.args]
    return cst.Call(func=func, args=args)


def _build_percent_binop(match: FormatPercentUsageMatch) -> cst.BinaryOperation:
    """
    "{},{}".format(h, w) / "{0},{1}".format(h, w)  ->  "%s,%s" % (h, w)
    """
    inner = _get_string_inner(match.template)
    new_inner = _format_inner_to_percent(inner)
    new_tmpl = _replace_string_inner(match.template, new_inner)

    if len(match.args) == 1:
        right: cst.BaseExpression = match.args[0]
    else:
        elements = [cst.Element(value=a) for a in match.args]
        right = cst.Tuple(elements=elements)

    return cst.BinaryOperation(
        left=new_tmpl,
        operator=cst.Modulo(),
        right=right,
    )


# --- variant 映射：percent / format ---

_VARIANT_KEY_TO_FORM: dict[str, FormatPercentForm] = {
    # 百分号形式: "%s" % args
    "percent": FormatPercentForm.PERCENT,
    "%":       FormatPercentForm.PERCENT,
    "percent_op": FormatPercentForm.PERCENT,

    # format 形式: "{}".format(args)
    "format":      FormatPercentForm.FORMAT,
    "format_call": FormatPercentForm.FORMAT,
}


@register_rule
class FormatPercentUsageRule(BaseRule):
    """
    "%s,%s" % (h, w)  <->  "{},{}".format(h, w) / "{0},{1}".format(h, w)

    多形态方向约定（基于新的 RuleDirection）：

      - direction.mode == "AUTO":
            PERCENT  -> FORMAT
            FORMAT   -> PERCENT

      - direction.mode == "TO_VARIANT":
            direction.variant 为字符串 key：
                "percent" / "%" / "percent_op"
                "format" / "format_call"
            本规则将这些 key 映射到 FormatPercentForm，并在两种形态之间做对应转换。
    """

    rule_id = "refactoring.format_percent_usage"
    description = "字符串格式化：'%%s' % args <-> '{}'.format(args) / '{0}'.format(args)"
    variants = ("percent", "format")

    # ------- 根据 direction 决定目标形态 -------

    def _target_form_for(self, current: FormatPercentForm) -> FormatPercentForm | None:
        direction = self.direction

        # AUTO：两种形态互换
        if direction.mode == "AUTO":
            if current is FormatPercentForm.PERCENT:
                target = FormatPercentForm.FORMAT
            elif current is FormatPercentForm.FORMAT:
                target = FormatPercentForm.PERCENT
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

    # ---- "%s" % args -> "{}".format(args) ----

    def leave_BinaryOperation(
        self,
        original_node: cst.BinaryOperation,
        updated_node: cst.BinaryOperation,
    ) -> cst.BaseExpression:
        match = match_format_percent_usage(updated_node)
        # 只在当前是 PERCENT、且目标为 FORMAT 时改写
        if match is None or match.form is not FormatPercentForm.PERCENT:
            return updated_node

        target_form = self._target_form_for(match.form)
        if target_form is None:
            return updated_node

        if target_form is FormatPercentForm.FORMAT:
            return _build_format_call(match)

        return updated_node

    # ---- "{}".format(args) / "{0}".format(args) -> "%s" % args ----

    def leave_Call(
        self,
        original_node: cst.Call,
        updated_node: cst.Call,
    ) -> cst.BaseExpression:
        match = match_format_percent_usage(updated_node)
        # 只在当前是 FORMAT、且目标为 PERCENT 时改写
        if match is None or match.form is not FormatPercentForm.FORMAT:
            return updated_node

        target_form = self._target_form_for(match.form)
        if target_form is None:
            return updated_node

        if target_form is FormatPercentForm.PERCENT:
            return _build_percent_binop(match)

        return updated_node
