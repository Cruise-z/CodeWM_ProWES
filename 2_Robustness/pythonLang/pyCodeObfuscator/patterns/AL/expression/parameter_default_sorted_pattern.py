# pyCodeObfuscator/patterns/AL/expression/parameter_default_sorted_pattern.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import libcst as cst


class ParameterDefaultSortedForm(str, Enum):
    """
    Two forms:
    - NO_REVERSE             : sorted(iterable)
    - EXPLICIT_REVERSE_FALSE : sorted(iterable, reverse=False)
    """
    NO_REVERSE = "no_reverse"
    EXPLICIT_REVERSE_FALSE = "explicit_reverse_false"


@dataclass
class ParameterDefaultSortedMatch:
    """
    Information for one match:
      - form        : current form
      - call        : the full sorted(...) call expression
      - func        : the called function (in practice Name('sorted'))
      - reverse_arg : the corresponding Arg if reverse=False is explicitly
                      present; otherwise None
    """
    form: ParameterDefaultSortedForm
    call: cst.Call
    func: cst.BaseExpression
    reverse_arg: Optional[cst.Arg]


def _is_reverse_false_arg(arg: cst.Arg) -> bool:
    """
    Determine whether an Arg has the form reverse=False.
    Currently only accepts the simplest literal form:
        - keyword is 'reverse'
        - value is Name('False')
    """
    if arg.keyword is None:
        return False
    if not isinstance(arg.keyword, cst.Name):
        return False
    if arg.keyword.value != "reverse":
        return False

    value = arg.value
    return isinstance(value, cst.Name) and value.value == "False"


def _match_no_reverse(call: cst.Call) -> Optional[ParameterDefaultSortedMatch]:
    """
    Match:
        sorted(iterable)
    or:
        sorted(iterable, key=..., <other keywords>...)
    provided that there is **no reverse=... argument at all**.
    """
    # Must be sorted(...)
    func = call.func
    if not (isinstance(func, cst.Name) and func.value == "sorted"):
        return None

    # Existing reverse arguments are not allowed.
    for arg in call.args:
        if arg.keyword is None:
            continue
        if isinstance(arg.keyword, cst.Name) and arg.keyword.value == "reverse":
            # reverse=... is already present, so this is not the NO_REVERSE
            # form regardless of the value.
            return None

    # If it passes the checks, treat it as NO_REVERSE.
    return ParameterDefaultSortedMatch(
        form=ParameterDefaultSortedForm.NO_REVERSE,
        call=call,
        func=func,
        reverse_arg=None,
    )


def _match_explicit_reverse_false(
    call: cst.Call,
) -> Optional[ParameterDefaultSortedMatch]:
    """
    Match:
        sorted(iterable, reverse=False)
    or:
        sorted(iterable, key=..., reverse=False, ...)
    As long as one reverse=False exists, treat it as this form.
    """
    func = call.func
    if not (isinstance(func, cst.Name) and func.value == "sorted"):
        return None

    found: Optional[cst.Arg] = None
    for arg in call.args:
        if _is_reverse_false_arg(arg):
            found = arg
            break

    if found is None:
        return None

    return ParameterDefaultSortedMatch(
        form=ParameterDefaultSortedForm.EXPLICIT_REVERSE_FALSE,
        call=call,
        func=func,
        reverse_arg=found,
    )


def match_parameter_default_sorted(
    node: cst.CSTNode,
) -> Optional[ParameterDefaultSortedMatch]:
    """
    Top-level matching entry point.

    Only applies to sorted(...) call expressions:
      - sorted(iterable)
      - sorted(iterable, reverse=False)
    """
    if not isinstance(node, cst.Call):
        return None

    # Prefer the explicit form first because it is more specific.
    m = _match_explicit_reverse_false(node)
    if m is not None:
        return m

    return _match_no_reverse(node)
