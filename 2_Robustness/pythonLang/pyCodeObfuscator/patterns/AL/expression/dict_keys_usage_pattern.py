# pyCodeObfuscator/patterns/AL/expression/dict_keys_usage_pattern.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import libcst as cst


class DictKeysForm(str, Enum):
    """
    两种形态：

    - DIRECT_IN:  'Alice' in d
    - KEYS_API : 'Alice' in d.keys()
    """
    DIRECT_IN = "direct_in"
    KEYS_API = "keys_api"


@dataclass
class DictKeysUsageMatch:
    """
    'key in d' <-> 'key in d.keys()' 的一次命中信息。
    """
    form: DictKeysForm
    comparison: cst.Comparison
    key_expr: cst.BaseExpression     # 'Alice'
    dict_expr: cst.BaseExpression    # d 或 obj.dict 等


def _match_direct_in(comp: cst.Comparison) -> Optional[DictKeysUsageMatch]:
    """
    匹配 'key in d' 形式。
    """
    if len(comp.comparisons) != 1:
        return None

    target = comp.comparisons[0]
    if not isinstance(target.operator, cst.In):
        return None

    comparator = target.comparator
    # 只接受 Name 或 Attribute 作为容器表达式（d / obj.d）
    if not isinstance(comparator, (cst.Name, cst.Attribute)):
        return None

    return DictKeysUsageMatch(
        form=DictKeysForm.DIRECT_IN,
        comparison=comp,
        key_expr=comp.left,
        dict_expr=comparator,
    )


def _match_keys_api(comp: cst.Comparison) -> Optional[DictKeysUsageMatch]:
    """
    匹配 'key in d.keys()' 形式。
    """
    if len(comp.comparisons) != 1:
        return None

    target = comp.comparisons[0]
    if not isinstance(target.operator, cst.In):
        return None

    comparator = target.comparator

    # 'key in d.keys()'
    if not isinstance(comparator, cst.Call):
        return None

    func = comparator.func
    if not isinstance(func, cst.Attribute):
        return None

    # attr 必须是 .keys
    if not isinstance(func.attr, cst.Name) or func.attr.value != "keys":
        return None

    # d 或 obj.d
    if not isinstance(func.value, (cst.Name, cst.Attribute)):
        return None

    # d.keys() 不接受参数
    if comparator.args:
        return None

    return DictKeysUsageMatch(
        form=DictKeysForm.KEYS_API,
        comparison=comp,
        key_expr=comp.left,
        dict_expr=func.value,
    )


def match_dict_keys_usage(
    expr: cst.BaseExpression,
) -> Optional[DictKeysUsageMatch]:
    """
    在一个表达式上尝试匹配：

      - 'key in d'
      - 'key in d.keys()'

    命中返回 DictKeysUsageMatch，否则返回 None。
    """
    if not isinstance(expr, cst.Comparison):
        return None

    # 先判定更具体的 keys() 形式，再判定裸 in
    m = _match_keys_api(expr)
    if m is not None:
        return m

    return _match_direct_in(expr)
