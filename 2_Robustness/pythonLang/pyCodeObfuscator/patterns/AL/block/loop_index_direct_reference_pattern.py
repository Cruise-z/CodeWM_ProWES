# pyCodeObfuscator/patterns/AL/block/loop_index_direct_reference_pattern.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import libcst as cst


class LoopIndexForm(str, Enum):
    """
    这条规则目前有两种形态：

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
    命中 “index-based <-> element-based” 循环重构 的匹配信息。
    """
    form: LoopIndexForm          # 当前是哪种形态
    for_node: cst.For            # 命中的 for 节点
    list_name: str               # 列表变量名，如 currencies
    index_name: Optional[str] = None    # index 变量名，如 i（INDEX_BASED 时使用）
    element_name: Optional[str] = None  # 元素变量名，如 currency（ELEMENT_BASED 时使用）


def _match_range_len_iter(expr: cst.BaseExpression) -> Optional[str]:
    """
    匹配 range(len(x)) 这种形式，返回 x 的名字；否则返回 None。

    例如:
        range(len(currencies)) -> "currencies"
    """
    # 匹配 range(...)
    if not isinstance(expr, cst.Call):
        return None
    if not isinstance(expr.func, cst.Name) or expr.func.value != "range":
        return None
    if len(expr.args) != 1:
        return None

    arg0 = expr.args[0].value

    # 匹配 len(x)
    if not isinstance(arg0, cst.Call):
        return None
    if not isinstance(arg0.func, cst.Name) or arg0.func.value != "len":
        return None
    if len(arg0.args) != 1:
        return None

    inner = arg0.args[0].value
    if not isinstance(inner, cst.Name):
        return None

    return inner.value  # list 变量名


def match_loop_index_direct_reference(
    node: cst.CSTNode,
) -> Optional[LoopIndexDirectReferenceMatch]:
    """
    在一个节点上尝试匹配 “for i in range(len(xs)) <-> for x in xs” 这种结构。

    命中时返回 LoopIndexDirectReferenceMatch，否则返回 None。
    """
    if not isinstance(node, cst.For):
        return None

    # ---------- 形态 1：INDEX_BASED ----------
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

    # ---------- 形态 2：ELEMENT_BASED ----------
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
