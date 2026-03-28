# pyCodeObfuscator/patterns/AL/block/initialize_ways_pattern.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

import libcst as cst


class InitializeWaysForm(str, Enum):
    """
    Two initialization-style forms:
    - DICT_CALL            : d = dict(name="1")
    - EMPTY_THEN_SUBSCRIPT : d = {}; d["name"] = "1"
    """
    DICT_CALL = "dict_call"
    EMPTY_THEN_SUBSCRIPT = "empty_then_subscript"


@dataclass
class InitializeWaysMatch:
    """
    Match information for one initialization-style pattern.

    Common fields:
      - form       : current form (DICT_CALL / EMPTY_THEN_SUBSCRIPT)
      - target     : variable name being initialized (currently only simple Name is matched)
      - first_stmt : first simple statement participating in the pattern
      - second_stmt: second simple statement for the two-line form; None for the single-line form

    Extra fields:
      - call       : if the form is DICT_CALL, this is the Call node on the RHS; otherwise None
      - keys       : if the form is EMPTY_THEN_SUBSCRIPT, this is the list of subscript keys (the current implementation only matches one)
      - values     : list of initialized values, used by both forms
    """
    form: InitializeWaysForm
    target: cst.Name
    first_stmt: cst.SimpleStatementLine
    second_stmt: Optional[cst.SimpleStatementLine]

    call: Optional[cst.Call]
    keys: List[cst.BaseExpression]
    values: List[cst.BaseExpression]


# ---------------------------
# Single-line form: d = dict(name="1")
# ---------------------------


def _match_dict_call_single(
    stmt: cst.SimpleStatementLine,
) -> Optional[InitializeWaysMatch]:
    """
    Match:
        d = dict(name="1", age=2, ...)
    Constraints:
      - only handle a single small statement
      - left side must be a simple variable name
      - right side must be a call to the built-in dict, and all parameters must be keyword arguments
    """
    if len(stmt.body) != 1:
        return None

    small = stmt.body[0]
    if not isinstance(small, cst.Assign):
        return None

    # Only handle a single target: d = ...
    if len(small.targets) != 1:
        return None

    assign_target = small.targets[0]
    target_expr = assign_target.target

    if not isinstance(target_expr, cst.Name):
        return None

    value = small.value
    if not isinstance(value, cst.Call):
        return None

    # Require a dict(...) call
    func = value.func
    if not (isinstance(func, cst.Name) and func.value == "dict"):
        return None

    values: List[cst.BaseExpression] = []

    # Only accept keyword-style arguments: dict(name="1", age=2)
    if not value.args:
        return None

    for arg in value.args:
        if arg.keyword is None:
            # Do not handle positional arguments or **kwargs yet
            return None
        values.append(arg.value)

    return InitializeWaysMatch(
        form=InitializeWaysForm.DICT_CALL,
        target=target_expr,
        first_stmt=stmt,
        second_stmt=None,
        call=value,
        keys=[],  # Single-line dict() calls do not use keys for now
        values=values,
    )


def match_initialize_ways_single(
    node: cst.CSTNode,
) -> Optional[InitializeWaysMatch]:
    """
    Matching entry point for the single-line form:
        d = dict(name="1")
    """
    if not isinstance(node, cst.SimpleStatementLine):
        return None

    return _match_dict_call_single(node)


# ------------------------------------------
# Two-line form: d = {}; d["name"] = "1"
# ------------------------------------------


def _match_empty_dict_assign(
    stmt: cst.SimpleStatementLine,
) -> Optional[cst.Name]:
    """
    Match:
        d = {}
    Or:
        d = dict()
    Return the initialized variable name as a Name.
    """
    if len(stmt.body) != 1:
        return None

    small = stmt.body[0]
    if not isinstance(small, cst.Assign):
        return None

    if len(small.targets) != 1:
        return None

    assign_target = small.targets[0]
    target_expr = assign_target.target
    if not isinstance(target_expr, cst.Name):
        return None

    value = small.value

    # 1) Empty literal: d = {}
    if isinstance(value, cst.Dict):
        if len(value.elements) == 0:
            return target_expr
        return None

    # 2) Empty dict() call: d = dict()
    if isinstance(value, cst.Call):
        func = value.func
        if isinstance(func, cst.Name) and func.value == "dict":
            if not value.args:
                return target_expr

    return None


def _extract_subscript_key_value(
    stmt: cst.SimpleStatementLine,
    target_name: cst.Name,
) -> Optional[Tuple[cst.BaseExpression, cst.BaseExpression]]:
    """
    Match:
        d["name"] = value
    where d is target_name.
    """
    if len(stmt.body) != 1:
        return None

    small = stmt.body[0]
    if not isinstance(small, cst.Assign):
        return None

    if len(small.targets) != 1:
        return None

    assign_target = small.targets[0]
    subscript = assign_target.target

    if not isinstance(subscript, cst.Subscript):
        return None

    # Chained subscripts such as d["name"][...] are not supported yet; only a single d[...] layer is handled
    base = subscript.value
    if not (isinstance(base, cst.Name) and base.value == target_name.value):
        return None

    # Only handle a single subscript dimension: d[...]
    slices = subscript.slice
    # Different versions of libcst may use tuple or list here; handle both uniformly as a sequence
    if not isinstance(slices, (list, tuple)) or len(slices) != 1:
        return None

    elem = slices[0]
    if not isinstance(elem, cst.SubscriptElement):
        return None

    index = elem.slice
    if not isinstance(index, cst.Index):
        return None

    key_expr = index.value
    value_expr = small.value

    return key_expr, value_expr


def match_initialize_ways_pair(
    first: cst.CSTNode,
    second: cst.CSTNode,
) -> Optional[InitializeWaysMatch]:
    """
    Matching entry point for the two-line form:

        d = {}
        d["name"] = "1"

    Only check this pattern across two consecutive SimpleStatementLine nodes.
    """
    if not (
        isinstance(first, cst.SimpleStatementLine)
        and isinstance(second, cst.SimpleStatementLine)
    ):
        return None

    target = _match_empty_dict_assign(first)
    if target is None:
        return None

    kv = _extract_subscript_key_value(second, target)
    if kv is None:
        return None

    key_expr, value_expr = kv

    return InitializeWaysMatch(
        form=InitializeWaysForm.EMPTY_THEN_SUBSCRIPT,
        target=target,
        first_stmt=first,
        second_stmt=second,
        call=None,
        keys=[key_expr],
        values=[value_expr],
    )
