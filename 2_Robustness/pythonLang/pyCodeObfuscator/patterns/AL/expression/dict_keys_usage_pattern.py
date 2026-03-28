# pyCodeObfuscator/patterns/AL/expression/dict_keys_usage_pattern.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import libcst as cst


class DictKeysForm(str, Enum):
    """
    Two forms:

    - DIRECT_IN:  'Alice' in d
    - KEYS_API : 'Alice' in d.keys()
    """
    DIRECT_IN = "direct_in"
    KEYS_API = "keys_api"


@dataclass
class DictKeysUsageMatch:
    """
    Match information for one occurrence of 'key in d' <-> 'key in d.keys()'.
    """
    form: DictKeysForm
    comparison: cst.Comparison
    key_expr: cst.BaseExpression     # 'Alice'
    dict_expr: cst.BaseExpression    # d or obj.dict, etc.


def _match_direct_in(comp: cst.Comparison) -> Optional[DictKeysUsageMatch]:
    """
    Match the form 'key in d'.
    """
    if len(comp.comparisons) != 1:
        return None

    target = comp.comparisons[0]
    if not isinstance(target.operator, cst.In):
        return None

    comparator = target.comparator
    # Only accept Name or Attribute as the container expression (d / obj.d)
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
    Match the form 'key in d.keys()'.
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

    # attr must be .keys
    if not isinstance(func.attr, cst.Name) or func.attr.value != "keys":
        return None

    # d or obj.d
    if not isinstance(func.value, (cst.Name, cst.Attribute)):
        return None

    # d.keys() must not take arguments
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
    Try to match on an expression:

      - 'key in d'
      - 'key in d.keys()'

    Return DictKeysUsageMatch on success, otherwise return None.
    """
    if not isinstance(expr, cst.Comparison):
        return None

    # Check the more specific keys() form first, then the bare in form
    m = _match_keys_api(expr)
    if m is not None:
        return m

    return _match_direct_in(expr)
