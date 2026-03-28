# pyCodeObfuscator/patterns/AL/block/loop_index_direct_reference_pattern.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import libcst as cst


class LoopIndexForm(str, Enum):
    """
    This rule currently has two forms:

    - INDEX_BASED:
        for i in range(len(currencies)):
            ...

    - ELEMENT_BASED:
        for currency in currencies:
            ...
    """
    INDEX_BASED = "index_based"
    ELEMENT_BASED = "element_based"


@dataclass
class LoopIndexDirectReferenceMatch:
    """
    Match information for the "index-based <-> element-based" loop refactor.
    """
    form: LoopIndexForm          # Current form
    for_node: cst.For            # Matched for node
    list_name: str               # List variable name, for example currencies
    index_name: Optional[str] = None    # Index variable name, for example i (used in INDEX_BASED)
    element_name: Optional[str] = None  # Element variable name, for example currency (used in ELEMENT_BASED)


def _match_range_len_iter(expr: cst.BaseExpression) -> Optional[str]:
    """
    Match the form range(len(x)) and return the name of x; otherwise return None.

    Example:
        range(len(currencies)) -> "currencies"
    """
    # Match range(...)
    if not isinstance(expr, cst.Call):
        return None
    if not isinstance(expr.func, cst.Name) or expr.func.value != "range":
        return None
    if len(expr.args) != 1:
        return None

    arg0 = expr.args[0].value

    # Match len(x)
    if not isinstance(arg0, cst.Call):
        return None
    if not isinstance(arg0.func, cst.Name) or arg0.func.value != "len":
        return None
    if len(arg0.args) != 1:
        return None

    inner = arg0.args[0].value
    if not isinstance(inner, cst.Name):
        return None

    return inner.value  # list variable name


def match_loop_index_direct_reference(
    node: cst.CSTNode,
) -> Optional[LoopIndexDirectReferenceMatch]:
    """
    Try to match a structure like "for i in range(len(xs)) <-> for x in xs" on a node.

    Return LoopIndexDirectReferenceMatch on success, otherwise return None.
    """
    if not isinstance(node, cst.For):
        return None

    # ---------- Form 1: INDEX_BASED ----------
    # for i in range(len(xs)):
    if isinstance(node.target, cst.Name):
        index_name = node.target.value
        list_name = _match_range_len_iter(node.iter)
        if list_name is not None:
            return LoopIndexDirectReferenceMatch(
                form=LoopIndexForm.INDEX_BASED,
                for_node=node,
                list_name=list_name,
                index_name=index_name,
                element_name=None,
            )

    # ---------- Form 2: ELEMENT_BASED ----------
    # for element in xs:
    if isinstance(node.target, cst.Name) and isinstance(node.iter, cst.Name):
        element_name = node.target.value
        list_name = node.iter.value
        return LoopIndexDirectReferenceMatch(
            form=LoopIndexForm.ELEMENT_BASED,
            for_node=node,
            list_name=list_name,
            index_name=None,
            element_name=element_name,
        )

    return None
