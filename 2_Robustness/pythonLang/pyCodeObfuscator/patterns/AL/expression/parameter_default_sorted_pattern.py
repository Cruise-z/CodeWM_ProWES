# pyCodeObfuscator/patterns/AL/expression/parameter_default_sorted_pattern.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import libcst as cst


class ParameterDefaultSortedForm(str, Enum):
    """
    两种形态：
    - NO_REVERSE             : sorted(iterable)
    - EXPLICIT_REVERSE_FALSE : sorted(iterable, reverse=False)
    """
    NO_REVERSE = "no_reverse"
    EXPLICIT_REVERSE_FALSE = "explicit_reverse_false"


@dataclass
class ParameterDefaultSortedMatch:
    """
    一次命中的信息：
      - form        : 当前形态
      - call        : 整个 sorted(...) 调用表达式
      - func        : 调用的函数（理论上就是 Name('sorted')）
      - reverse_arg : 若有显式 reverse=False，则记录对应的 Arg；否则为 None
    """
    form: ParameterDefaultSortedForm
    call: cst.Call
    func: cst.BaseExpression
    reverse_arg: Optional[cst.Arg]


def _is_reverse_false_arg(arg: cst.Arg) -> bool:
    """
    判断一个 Arg 是否形如 reverse=False。
    目前只接受最简单的字面形式：
        - keyword 名为 'reverse'
        - value 为 Name('False')
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
    匹配：
        sorted(iterable)
    或：
        sorted(iterable, key=..., <其它 keyword>...)
    但前提是 **没有任何 reverse=... 参数**。
    """
    # 必须是 sorted(...)
    func = call.func
    if not (isinstance(func, cst.Name) and func.value == "sorted"):
        return None

    # 不允许已有 reverse 参数
    for arg in call.args:
        if arg.keyword is None:
            continue
        if isinstance(arg.keyword, cst.Name) and arg.keyword.value == "reverse":
            # 已经有 reverse=...，无论值是什么，都不算 NO_REVERSE 形态
            return None

    # 通过即认为是 NO_REVERSE
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
    匹配：
        sorted(iterable, reverse=False)
    或：
        sorted(iterable, key=..., reverse=False, ...)
    只要存在一个 reverse=False，就视为该形态。
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
    顶层匹配入口。

    只对 sorted(...) 的调用表达式生效：
      - sorted(iterable)
      - sorted(iterable, reverse=False)
    """
    if not isinstance(node, cst.Call):
        return None

    # 优先判断 explicit 形态（更具体）
    m = _match_explicit_reverse_false(node)
    if m is not None:
        return m

    return _match_no_reverse(node)
