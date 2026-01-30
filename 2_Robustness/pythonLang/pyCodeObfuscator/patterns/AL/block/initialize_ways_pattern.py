# pyCodeObfuscator/patterns/AL/block/initialize_ways_pattern.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

import libcst as cst


class InitializeWaysForm(str, Enum):
    """
    初始化风格的两种形态：
    - DICT_CALL            : d = dict(name="1")
    - EMPTY_THEN_SUBSCRIPT : d = {}; d["name"] = "1"
    """
    DICT_CALL = "dict_call"
    EMPTY_THEN_SUBSCRIPT = "empty_then_subscript"


@dataclass
class InitializeWaysMatch:
    """
    一次初始化模式命中的信息。

    通用字段：
      - form       : 当前形态（DICT_CALL / EMPTY_THEN_SUBSCRIPT）
      - target     : 被初始化的变量名（目前只匹配简单 Name）
      - first_stmt : 参与模式的第一条简单语句
      - second_stmt: 若是两行形式，则为第二条简单语句；单行形式则为 None

    额外字段：
      - call       : 若是 DICT_CALL，则为右侧的 Call 节点；否则为 None
      - keys       : 若是 EMPTY_THEN_SUBSCRIPT，则为下标 key 列表（当前实现只匹配一个）
      - values     : 初始化 value 列表（两种形态都会用到）
    """
    form: InitializeWaysForm
    target: cst.Name
    first_stmt: cst.SimpleStatementLine
    second_stmt: Optional[cst.SimpleStatementLine]

    call: Optional[cst.Call]
    keys: List[cst.BaseExpression]
    values: List[cst.BaseExpression]


# ---------------------------
# 单行：d = dict(name="1")
# ---------------------------


def _match_dict_call_single(
    stmt: cst.SimpleStatementLine,
) -> Optional[InitializeWaysMatch]:
    """
    匹配：
        d = dict(name="1", age=2, ...)
    约束：
      - 只处理单一小语句
      - 左侧是简单变量名
      - 右侧是对内建 dict 的调用，且参数全部为 keyword 形式
    """
    if len(stmt.body) != 1:
        return None

    small = stmt.body[0]
    if not isinstance(small, cst.Assign):
        return None

    # 只处理单一目标：d = ...
    if len(small.targets) != 1:
        return None

    assign_target = small.targets[0]
    target_expr = assign_target.target

    if not isinstance(target_expr, cst.Name):
        return None

    value = small.value
    if not isinstance(value, cst.Call):
        return None

    # 要求是 dict(...) 调用
    func = value.func
    if not (isinstance(func, cst.Name) and func.value == "dict"):
        return None

    values: List[cst.BaseExpression] = []

    # 只接受 keyword 形式的参数：dict(name="1", age=2)
    if not value.args:
        return None

    for arg in value.args:
        if arg.keyword is None:
            # 带位置参数或者 **kwargs 的情况先不处理
            return None
        values.append(arg.value)

    return InitializeWaysMatch(
        form=InitializeWaysForm.DICT_CALL,
        target=target_expr,
        first_stmt=stmt,
        second_stmt=None,
        call=value,
        keys=[],  # 单行 dict 调用暂不使用 keys
        values=values,
    )


def match_initialize_ways_single(
    node: cst.CSTNode,
) -> Optional[InitializeWaysMatch]:
    """
    单行版本匹配入口：
        d = dict(name="1")
    """
    if not isinstance(node, cst.SimpleStatementLine):
        return None

    return _match_dict_call_single(node)


# ------------------------------------------
# 两行：d = {}; d["name"] = "1" 这样的模式
# ------------------------------------------


def _match_empty_dict_assign(
    stmt: cst.SimpleStatementLine,
) -> Optional[cst.Name]:
    """
    匹配：
        d = {}
    或：
        d = dict()
    返回被初始化的变量名 Name。
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

    # 1) 空字面量：d = {}
    if isinstance(value, cst.Dict):
        if len(value.elements) == 0:
            return target_expr
        return None

    # 2) 空 dict() 调用：d = dict()
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
    匹配：
        d["name"] = value
    其中 d 是 target_name。
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

    # d["name"][...] 这样的链式下标暂不支持，只处理 d[...] 一层
    base = subscript.value
    if not (isinstance(base, cst.Name) and base.value == target_name.value):
        return None

    # 只处理单一下标维度：d[...]
    slices = subscript.slice
    # 不同版本的 libcst 这里可能是 tuple 或 list，统一当做 sequence 处理
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
    两行版本匹配入口：

        d = {}
        d["name"] = "1"

    只在两个连续的 SimpleStatementLine 之间检查这种模式。
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
