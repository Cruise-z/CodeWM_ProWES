# pyCodeObfuscator/rules/NL/naming_style.py
from __future__ import annotations

from typing import Optional

import libcst as cst

from ...core.rule_base import BaseRule, RuleDirection, register_rule
from ...patterns.NL.naming_style_pattern import (
    match_naming_style,
    NamingStyle,
    NamingStyleMatch,
    build_name,
)


def _pick_auto_target_style(current: NamingStyle) -> NamingStyle:
    """
    Rotation strategy in AUTO mode (deterministic for easier testing):
      CAMEL             -> SNAKE
      SNAKE             -> PASCAL_UNDERSCORE
      PASCAL_UNDERSCORE -> CAMEL
    """
    if current is NamingStyle.CAMEL:
        return NamingStyle.SNAKE
    if current is NamingStyle.SNAKE:
        return NamingStyle.PASCAL_UNDERSCORE
    if current is NamingStyle.PASCAL_UNDERSCORE:
        return NamingStyle.CAMEL
    return current


# Allowed aliases -> NamingStyle
_VARIANT_KEY_TO_STYLE: dict[str, NamingStyle] = {
    # Camel-style aliases
    "camel": NamingStyle.CAMEL,
    "pascal": NamingStyle.CAMEL,
    "camelcase": NamingStyle.CAMEL,
    "pascalcase": NamingStyle.CAMEL,

    # Snake-style aliases
    "snake": NamingStyle.SNAKE,
    "snake_case": NamingStyle.SNAKE,
    "snakecase": NamingStyle.SNAKE,

    # user_Add_Num-style aliases
    "underscore": NamingStyle.PASCAL_UNDERSCORE,
    "pascal_underscore": NamingStyle.PASCAL_UNDERSCORE,
    "user_add_num_style": NamingStyle.PASCAL_UNDERSCORE,
}


@register_rule
class NamingStyleRule(BaseRule):
    """
    Convert among three naming styles:

        UserAddNum    # CAMEL
        user_add_num  # SNAKE
        user_Add_Num  # PASCAL_UNDERSCORE

    Multi-variant direction convention (based on RuleDirection):

      - direction.mode == "AUTO":
            Detect the current style and rotate among the three styles:
                CAMEL -> SNAKE -> PASCAL_UNDERSCORE -> CAMEL

      - direction.mode == "TO_VARIANT":
            direction.variant is a string key:
                "camel" / "snake" / "underscore" / "pascal_underscore" / ...
            This rule maps those keys to NamingStyle and rewrites names into the target style.
    """

    rule_id = "refactoring.naming_style"
    description = "Convert variable/parameter naming styles (Camel / snake / user_Add_Num)"

    # Declare the variant names supported by this rule (mainly for CLI/docs, optional)
    variants = ("camel", "snake", "pascal_underscore")

    def _target_style_for(self, match: NamingStyleMatch) -> Optional[NamingStyle]:
        cur = match.style
        direction = self.direction

        # ---- AUTO: rotate among the three styles ----
        if direction.mode == "AUTO":
            target = _pick_auto_target_style(cur)

        # ---- TO_VARIANT: choose the target style based on the string key ----
        elif direction.mode == "TO_VARIANT":
            key = direction.variant
            if key is None:
                return None
            style = _VARIANT_KEY_TO_STYLE.get(key.lower())
            if style is None:
                # Unknown variant key: do not rewrite
                return None
            target = style

        else:
            # Unknown mode: do not rewrite for safety
            return None

        # If it is already in the target style, leave it unchanged
        if target is cur:
            return None
        return target

    def leave_Name(
        self,
        original_node: cst.Name,
        updated_node: cst.Name,
    ) -> cst.Name:
        """
        Try to convert naming style for every Name node.

        Current simple implementation: infer style purely from the name itself,
        without distinguishing variables, parameters, function names, etc.
        If you want finer-grained control later, you can filter with metadata.
        """
        match = match_naming_style(updated_node)
        if match is None:
            return updated_node

        target_style = self._target_style_for(match)
        if target_style is None:
            return updated_node

        new_name = build_name(target_style, match.words)
        return updated_node.with_changes(value=new_name)
