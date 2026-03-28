# pyCodeObfuscator/patterns/AL/block/for_to_list_comprehension_pattern.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import libcst as cst


class ForListCompForm(str, Enum):
    """
    Two forms:
    - LOOP_BASED:
        cubes = []
        for i in range(20):
            cubes.append(i**3)

    - COMPREHENSION_BASED:
        cubes = [i**3 for i in range(20)]
    """
    LOOP_BASED = "loop_based"
    COMPREHENSION_BASED = "comprehension_based"


@dataclass
class ForListCompMatch:
    """
    Match information for one for-loop <-> list comprehension occurrence.
    """
    form: ForListCompForm

    # Shared information
    target_name: str                 # cubes
    index_name: str                  # i
    iter_expr: cst.BaseExpression    # range(20)
    value_expr: cst.BaseExpression   # i**3

    # Statement context, used during rewriting
    assign_stmt: cst.SimpleStatementLine
    for_stmt: Optional[cst.For] = None  # Present in LOOP_BASED; may be None in COMPREHENSION_BASED


def _extract_single_assign(stmt: cst.BaseStatement) -> Optional[cst.Assign]:
    """
    Only accept simple assignments of the form "name = ...".
    """
    if not isinstance(stmt, cst.SimpleStatementLine):
        return None
    if len(stmt.body) != 1:
        return None
    inner = stmt.body[0]
    if not isinstance(inner, cst.Assign):
        return None
    if len(inner.targets) != 1:
        return None
    target = inner.targets[0].target
    if not isinstance(target, cst.Name):
        return None
    return inner


def _match_loop_based_pair(
    assign_stmt: cst.BaseStatement, next_stmt: Optional[cst.BaseStatement]
) -> Optional[ForListCompMatch]:
    """
    Match the LOOP_BASED form:

        cubes = []
        for i in range(20):
            cubes.append(i**3)
    """
    if next_stmt is None:
        return None

    assign = _extract_single_assign(assign_stmt)
    if assign is None:
        return None

    # cubes = []
    target = assign.targets[0].target
    if not isinstance(target, cst.Name):
        return None
    target_name = target.value

    if not isinstance(assign.value, cst.List):
        return None
    # Only accept the empty list [] here
    if assign.value.elements:
        return None

    # for i in range(20):
    if not isinstance(next_stmt, cst.For):
        return None
    for_stmt = next_stmt
    if not isinstance(for_stmt.target, cst.Name):
        return None
    index_name = for_stmt.target.value

    iter_expr = for_stmt.iter

    # Loop body: a single statement "cubes.append(expr)"
    if not isinstance(for_stmt.body, cst.IndentedBlock):
        return None
    body = for_stmt.body.body
    if len(body) != 1:
        return None
    only_stmt = body[0]
    if not isinstance(only_stmt, cst.SimpleStatementLine):
        return None
    if len(only_stmt.body) != 1:
        return None
    expr = only_stmt.body[0]
    if not isinstance(expr, cst.Expr):
        return None
    call = expr.value
    if not isinstance(call, cst.Call):
        return None

    # cubes.append(...)
    func = call.func
    if not isinstance(func, cst.Attribute):
        return None
    if not isinstance(func.value, cst.Name):
        return None
    if func.value.value != target_name:
        return None
    if not isinstance(func.attr, cst.Name) or func.attr.value != "append":
        return None

    # Arguments: a single arg, value_expr
    if len(call.args) != 1:
        return None
    value_expr = call.args[0].value

    return ForListCompMatch(
        form=ForListCompForm.LOOP_BASED,
        target_name=target_name,
        index_name=index_name,
        iter_expr=iter_expr,
        value_expr=value_expr,
        assign_stmt=assign_stmt,
        for_stmt=for_stmt,
    )


def _match_comprehension_assign(
    assign_stmt: cst.BaseStatement,
) -> Optional[ForListCompMatch]:
    """
    Match the COMPREHENSION_BASED form:

        cubes = [i**3 for i in range(20)]
    """
    assign = _extract_single_assign(assign_stmt)
    if assign is None:
        return None

    target = assign.targets[0].target
    if not isinstance(target, cst.Name):
        return None
    target_name = target.value

    value = assign.value
    if not isinstance(value, cst.ListComp):
        return None

    # elt: i**3
    value_expr = value.elt

    # for i in range(20)
    comp_for = value.for_in
    if not isinstance(comp_for, cst.CompFor):
        return None
    # Do not handle multiple for / if clauses
    if comp_for.ifs or comp_for.inner_for_in is not None:
        return None

    target_node = comp_for.target
    # Only accept simple Name
    if not isinstance(target_node, cst.Name):
        return None
    index_name = target_node.value
    iter_expr = comp_for.iter

    return ForListCompMatch(
        form=ForListCompForm.COMPREHENSION_BASED,
        target_name=target_name,
        index_name=index_name,
        iter_expr=iter_expr,
        value_expr=value_expr,
        assign_stmt=assign_stmt,
        for_stmt=None,
    )


def match_for_list_comprehension_pair(
    assign_stmt: cst.BaseStatement,
    next_stmt: Optional[cst.BaseStatement],
) -> Optional[ForListCompMatch]:
    """
    Try to match on a pair of adjacent statements (assign_stmt, next_stmt):

    - LOOP_BASED:
        cubes = []
        for i in range(...):
            cubes.append(...)

    - COMPREHENSION_BASED:
        cubes = [ ... for i in range(...) ]

    Return ForListCompMatch on success, otherwise return None.
    """
    # Try the loop-based form first, which requires two statements
    m = _match_loop_based_pair(assign_stmt, next_stmt)
    if m is not None:
        return m

    # Then try the comprehension-based form, which only needs assign_stmt
    m = _match_comprehension_assign(assign_stmt)
    if m is not None:
        return m

    return None
