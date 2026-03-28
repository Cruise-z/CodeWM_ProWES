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
    Normalize / convert between:
      - sorted(arr) / sorted(arr, key=...)      (without explicitly writing reverse)
      - sorted(arr, reverse=False) / ...        (with explicit reverse=False)
    """

    rule_id = "refactoring.parameter_default_sorted"
    description = "Normalize usage of sorted(..., reverse=False) vs sorted(...)"
    variants = ("explicit_reverse_false", "no_reverse")

    _VARIANT_KEY_TO_FORM: dict[str, ParameterDefaultSortedForm] = {
        # Explicit reverse=False
        "explicit_reverse_false": ParameterDefaultSortedForm.EXPLICIT_REVERSE_FALSE,
        "explicit": ParameterDefaultSortedForm.EXPLICIT_REVERSE_FALSE,
        "reverse_false": ParameterDefaultSortedForm.EXPLICIT_REVERSE_FALSE,
        # Do not write the reverse parameter
        "no_reverse": ParameterDefaultSortedForm.NO_REVERSE,
        "implicit": ParameterDefaultSortedForm.NO_REVERSE,
    }

    def _target_form_for(
        self, current: ParameterDefaultSortedForm
    ) -> Optional[ParameterDefaultSortedForm]:
        direction = self.direction

        # AUTO mode: flip between the two forms
        if direction.mode == "AUTO":
            if current is ParameterDefaultSortedForm.NO_REVERSE:
                return ParameterDefaultSortedForm.EXPLICIT_REVERSE_FALSE
            if current is ParameterDefaultSortedForm.EXPLICIT_REVERSE_FALSE:
                return ParameterDefaultSortedForm.NO_REVERSE
            return None

        # Explicit target-form mode
        if direction.mode == "TO_VARIANT":
            key = direction.variant
            if key is None:
                return None
            form = self._VARIANT_KEY_TO_FORM.get(key.lower())
            if form is None or form is current:
                return None
            return form

        return None

    # Expression-level rule, attached directly to Call
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


# ---- Concrete rewrite logic -----------------------------------------------------------------


def _build_reverse_false_arg() -> cst.Arg:
    """
    Build a keyword argument: reverse=False
    Note: AssignEqual is used explicitly here, and the surrounding whitespace is set to "",
    so the generated code becomes `reverse=False` rather than `reverse = False`.
    """
    return cst.Arg(
        value=cst.Name("False"),
        keyword=cst.Name("reverse"),
        equal=cst.AssignEqual(
            whitespace_before=cst.SimpleWhitespace(""),
            whitespace_after=cst.SimpleWhitespace(""),
        ),
        # Other fields can keep their defaults:
        # comma=MaybeSentinel.DEFAULT, star="", whitespace_after_star="", whitespace_after_arg=""
    )


def _rewrite_no_reverse_to_explicit(
    match: ParameterDefaultSortedMatch,
) -> cst.Call:
    """
    sorted(arr) / sorted(arr, key=...)  ->  append reverse=False to the end of the argument list
    """
    call = match.call
    reverse_arg = _build_reverse_false_arg()

    # Directly append a new Arg to the end of the current argument list
    new_args: List[cst.Arg] = [*call.args, reverse_arg]
    return call.with_changes(args=new_args)


def _rewrite_explicit_to_no_reverse(
    match: ParameterDefaultSortedMatch,
) -> cst.Call:
    """
    sorted(arr, ..., reverse=False)  ->  remove reverse=False and also remove any extra trailing comma

    This needs special handling:
      - the argument before `reverse=False` usually carries a comma;
      - after removing reverse, if that comma is not cleaned up, the result becomes `sorted(arr, )`
    """
    call = match.call
    reverse_arg = match.reverse_arg
    if reverse_arg is None:
        return call

    # Remove the reverse=False Arg
    new_args: List[cst.Arg] = []
    for arg in call.args:
        if arg is reverse_arg:
            continue
        new_args.append(arg)

    # If removing it leaves no arguments, simply return an empty list of args
    if not new_args:
        return call.with_changes(args=())

    # Reset the comma on the last argument to MaybeSentinel.DEFAULT,
    # so Call._codegen_impl treats it as the final argument and does not force a trailing comma.
    last = new_args[-1].with_changes(comma=cst.MaybeSentinel.DEFAULT)
    new_args[-1] = last

    return call.with_changes(args=new_args)
