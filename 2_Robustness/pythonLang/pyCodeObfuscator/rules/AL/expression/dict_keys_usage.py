# pyCodeObfuscator/rules/AL/expression/dict_keys_usage.py
from __future__ import annotations

import libcst as cst

from ....core.rule_base import BaseRule, RuleDirection, register_rule
from ....patterns.AL.expression.dict_keys_usage_pattern import (
    match_dict_keys_usage,
    DictKeysForm,
    DictKeysUsageMatch,
)


# 将 variant 字符串映射到目标形态：
#   - "direct"/"direct_in"  ->  DIRECT_IN
#   - "keys"/"keys_api"     ->  KEYS_API
_VARIANT_KEY_TO_FORM: dict[str, DictKeysForm] = {
    "direct": DictKeysForm.DIRECT_IN,
    "direct_in": DictKeysForm.DIRECT_IN,
    "bare_in": DictKeysForm.DIRECT_IN,

    "keys": DictKeysForm.KEYS_API,
    "keys_api": DictKeysForm.KEYS_API,
    "keys_call": DictKeysForm.KEYS_API,
}


@register_rule
class DictKeysUsageRule(BaseRule):
    """
    多形态规则：

        'key' in d        (DIRECT_IN)
        'key' in d.keys() (KEYS_API)

    方向约定（基于新的 RuleDirection）：

      - direction.mode == "AUTO":
            DIRECT_IN  -> KEYS_API
            KEYS_API   -> DIRECT_IN

      - direction.mode == "TO_VARIANT":
            direction.variant 为字符串 key：
                "direct" / "direct_in" / "bare_in"
                "keys" / "keys_api" / "keys_call"
            本规则将这些 key 映射到 DictKeysForm，并在两种形态之间做对应转换。
    """

    rule_id = "refactoring.dict_keys_usage"
    description = "dict membership: 'key in d' <-> 'key in d.keys()'"
    variants = ("direct", "keys")

    # -------- 根据 direction 决定目标形态 --------

    def _target_form_for(self, current: DictKeysForm) -> DictKeysForm | None:
        direction = self.direction

        # AUTO：两种形态互换
        if direction.mode == "AUTO":
            if current is DictKeysForm.DIRECT_IN:
                target = DictKeysForm.KEYS_API
            elif current is DictKeysForm.KEYS_API:
                target = DictKeysForm.DIRECT_IN
            else:
                return None

        # TO_VARIANT：根据 variant 字符串决定目标形态
        elif direction.mode == "TO_VARIANT":
            key = direction.variant
            if key is None:
                return None
            form = _VARIANT_KEY_TO_FORM.get(key.lower())
            if form is None:
                # 不认识的 key：不改写
                return None
            target = form

        else:
            # 未知 mode：不改写
            return None

        # 当前形态已经是目标形态则不改写
        if target is current:
            return None

        return target

    # -------- 主重写逻辑 --------

    def leave_Comparison(
        self,
        original_node: cst.Comparison,
        updated_node: cst.Comparison,
    ) -> cst.Comparison:
        match = match_dict_keys_usage(updated_node)
        if match is None:
            return updated_node

        target_form = self._target_form_for(match.form)
        if target_form is None:
            return updated_node

        # DIRECT_IN -> KEYS_API
        if (
            match.form is DictKeysForm.DIRECT_IN
            and target_form is DictKeysForm.KEYS_API
        ):
            return _comparison_direct_to_keys(updated_node, match)

        # KEYS_API -> DIRECT_IN
        if (
            match.form is DictKeysForm.KEYS_API
            and target_form is DictKeysForm.DIRECT_IN
        ):
            return _comparison_keys_to_direct(updated_node, match)

        # 理论上不会走到，兜底
        return updated_node


def _comparison_direct_to_keys(
    node: cst.Comparison,
    match: DictKeysUsageMatch,
) -> cst.Comparison:
    """
    'key in d' -> 'key in d.keys()'
    """
    dict_expr = match.dict_expr

    keys_attr = cst.Attribute(
        value=dict_expr,
        attr=cst.Name("keys"),
    )
    new_comparator = cst.Call(func=keys_attr, args=[])

    target = node.comparisons[0]
    new_target = target.with_changes(comparator=new_comparator)

    return node.with_changes(comparisons=[new_target])


def _comparison_keys_to_direct(
    node: cst.Comparison,
    match: DictKeysUsageMatch,
) -> cst.Comparison:
    """
    'key in d.keys()' -> 'key in d'
    """
    new_comparator = match.dict_expr

    target = node.comparisons[0]
    new_target = target.with_changes(comparator=new_comparator)

    return node.with_changes(comparisons=[new_target])
