# pyCodeObfuscator/rules/AL/expression/dict_keys_usage.py
from __future__ import annotations

import libcst as cst

from ....core.rule_base import BaseRule, RuleDirection, register_rule
from ....patterns.AL.expression.dict_keys_usage_pattern import (
    match_dict_keys_usage,
    DictKeysForm,
    DictKeysUsageMatch,
)


# Map variant strings to target forms:
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
    Multi-form rule:

        'key' in d        (DIRECT_IN)
        'key' in d.keys() (KEYS_API)

    Direction conventions (based on the new RuleDirection):

      - direction.mode == "AUTO":
            DIRECT_IN  -> KEYS_API
            KEYS_API   -> DIRECT_IN

      - direction.mode == "TO_VARIANT":
            direction.variant is a string key:
                "direct" / "direct_in" / "bare_in"
                "keys" / "keys_api" / "keys_call"
            This rule maps those keys to DictKeysForm and converts between the
            two forms accordingly.
    """

    rule_id = "refactoring.dict_keys_usage"
    description = "dict membership: 'key in d' <-> 'key in d.keys()'"
    variants = ("direct", "keys")

    # -------- Determine the target form from direction --------

    def _target_form_for(self, current: DictKeysForm) -> DictKeysForm | None:
        direction = self.direction

        # AUTO: switch between the two forms.
        if direction.mode == "AUTO":
            if current is DictKeysForm.DIRECT_IN:
                target = DictKeysForm.KEYS_API
            elif current is DictKeysForm.KEYS_API:
                target = DictKeysForm.DIRECT_IN
            else:
                return None

        # TO_VARIANT: choose the target form from the variant string.
        elif direction.mode == "TO_VARIANT":
            key = direction.variant
            if key is None:
                return None
            form = _VARIANT_KEY_TO_FORM.get(key.lower())
            if form is None:
                # Unknown key: do not rewrite.
                return None
            target = form

        else:
            # Unknown mode: do not rewrite.
            return None

        # No rewrite is needed if the current form already matches the target.
        if target is current:
            return None

        return target

    # -------- Main rewrite logic --------

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

        # Fallback; should not be reached in practice.
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
