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
    (the pattern already guarantees that only %s appears, with no %d/%f/%% and so on)
    """
    return inner.replace("%s", "{}")


def _format_inner_to_percent(inner: str) -> str:
    """
    "{},{}" / "{0},{1}" -> "%s,%s"

    Assume inner has already passed the pattern's _check_format_template validation:
      - It contains only {} or {number}
      - It does not include complex cases such as {{ / }}
    """
    out_chars: list[str] = []
    i = 0
    n = len(inner)

    while i < n:
        ch = inner[i]
        if ch == "{":
            j = inner.find("}", i + 1)
            if j == -1:
                # This should not happen in theory (the pattern has already validated it), but keep a fallback here
                out_chars.append(ch)
                i += 1
            else:
                # Skip {...} and normalize everything to %s
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


# --- Variant mapping: percent / format ---

_VARIANT_KEY_TO_FORM: dict[str, FormatPercentForm] = {
    # Percent form: "%s" % args
    "percent": FormatPercentForm.PERCENT,
    "%":       FormatPercentForm.PERCENT,
    "percent_op": FormatPercentForm.PERCENT,

    # format form: "{}".format(args)
    "format":      FormatPercentForm.FORMAT,
    "format_call": FormatPercentForm.FORMAT,
}


@register_rule
class FormatPercentUsageRule(BaseRule):
    """
    "%s,%s" % (h, w)  <->  "{},{}".format(h, w) / "{0},{1}".format(h, w)

    Multi-variant direction rules (based on the new RuleDirection):

      - direction.mode == "AUTO":
            PERCENT  -> FORMAT
            FORMAT   -> PERCENT

      - direction.mode == "TO_VARIANT":
            direction.variant is a string key:
                "percent" / "%" / "percent_op"
                "format" / "format_call"
            This rule maps those keys to FormatPercentForm and performs the corresponding conversion between the two forms.
    """

    rule_id = "refactoring.format_percent_usage"
    description = "String formatting: '%%s' % args <-> '{}'.format(args) / '{0}'.format(args)"
    variants = ("percent", "format")

    # ------- Determine the target form from direction -------

    def _target_form_for(self, current: FormatPercentForm) -> FormatPercentForm | None:
        direction = self.direction

        # AUTO: swap between the two forms
        if direction.mode == "AUTO":
            if current is FormatPercentForm.PERCENT:
                target = FormatPercentForm.FORMAT
            elif current is FormatPercentForm.FORMAT:
                target = FormatPercentForm.PERCENT
            else:
                return None

        # TO_VARIANT: determine the target form from the variant string
        elif direction.mode == "TO_VARIANT":
            key = direction.variant
            if key is None:
                return None
            form = _VARIANT_KEY_TO_FORM.get(key.lower())
            if form is None:
                # Unknown key: do not rewrite
                return None
            target = form

        else:
            # Unknown mode: do not rewrite
            return None

        # Do not rewrite if the current form already matches the target
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
        # Rewrite only when the current form is PERCENT and the target is FORMAT
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
        # Rewrite only when the current form is FORMAT and the target is PERCENT
        if match is None or match.form is not FormatPercentForm.FORMAT:
            return updated_node

        target_form = self._target_form_for(match.form)
        if target_form is None:
            return updated_node

        if target_form is FormatPercentForm.PERCENT:
            return _build_percent_binop(match)

        return updated_node
