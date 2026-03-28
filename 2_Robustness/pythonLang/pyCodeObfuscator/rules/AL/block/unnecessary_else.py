# pyCodeObfuscator/rules/AL/block/unnecessary_else.py
from __future__ import annotations

from typing import List, Optional

import libcst as cst

from ....core.rule_base import BaseRule, RuleDirection, register_rule
from ....patterns.AL.block.unnecessary_else_pattern import (
    match_remove_unnecessary_else,
    RemoveElseForm,
    RemoveElseMatch,
)


# Provide a mapping from variant strings to forms: with_else / no_else
_VARIANT_KEY_TO_FORM: dict[str, RemoveElseForm] = {
    "with_else": RemoveElseForm.ORIGINAL,     # Form with else
    "has_else": RemoveElseForm.ORIGINAL,
    "original": RemoveElseForm.ORIGINAL,

    "no_else": RemoveElseForm.TRANSFORMED,    # Form with else removed
    "without_else": RemoveElseForm.TRANSFORMED,
    "removed_else": RemoveElseForm.TRANSFORMED,
    "transformed": RemoveElseForm.TRANSFORMED,
}


@register_rule
class RemoveUnnecessaryElseRule(BaseRule):
    """
    Two-form refactoring for removing unnecessary else:

    Form A (ORIGINAL / with_else):
        if cond:
            return ...
        else:
            # some code

    Form B (TRANSFORMED / no_else):
        if cond:
            return ...
        # some code

    Direction rules under the new RuleDirection structure:

      - direction.mode == "AUTO":
            ORIGINAL     -> TRANSFORMED
            TRANSFORMED  -> ORIGINAL

      - direction.mode == "TO_VARIANT":
            direction.variant is a string key:
                "with_else" / "has_else" / "original"
                "no_else" / "without_else" / "removed_else" / "transformed"
            This rule maps those keys to RemoveElseForm and performs the corresponding conversion between the two forms.
    """

    rule_id = "refactoring.remove_unnecessary_else"
    description = "Original <-> remove unnecessary else refactor"
    variants = ("with_else", "no_else")

    # ------- Determine the target form from direction -------

    def _target_form_for(self, match: RemoveElseMatch) -> Optional[RemoveElseForm]:
        cur = match.form
        direction = self.direction

        # AUTO: swap between the two forms
        if direction.mode == "AUTO":
            if cur is RemoveElseForm.ORIGINAL:
                target = RemoveElseForm.TRANSFORMED
            elif cur is RemoveElseForm.TRANSFORMED:
                target = RemoveElseForm.ORIGINAL
            else:
                return None

        # TO_VARIANT: determine the target form from the variant string
        elif direction.mode == "TO_VARIANT":
            key = direction.variant
            if key is None:
                return None
            form = _VARIANT_KEY_TO_FORM.get(key.lower())
            if form is None:
                # Unknown key: do not rewrite
                return None
            target = form

        else:
            # Unknown mode: do not rewrite
            return None

        # Do not rewrite if the current form already matches the target
        if target is cur:
            return None

        return target

    # ------- Main rewrite logic: handle if/else inside indented blocks -------

    def leave_IndentedBlock(
        self,
        original_node: cst.IndentedBlock,
        updated_node: cst.IndentedBlock,
    ) -> cst.IndentedBlock:
        body: List[cst.BaseStatement] = list(updated_node.body)
        new_body: List[cst.BaseStatement] = []

        i = 0
        n = len(body)

        while i < n:
            stmt = body[i]

            match = match_remove_unnecessary_else(stmt)

            # Pattern not matched, keep unchanged
            if match is None:
                new_body.append(stmt)
                i += 1
                continue

            target_form = self._target_form_for(match)
            if target_form is None:
                # The current direction does not require or allow rewriting this if
                new_body.append(stmt)
                i += 1
                continue

            # ---------- ORIGINAL (with else) -> TRANSFORMED (without else) ----------
            if (
                match.form is RemoveElseForm.ORIGINAL
                and target_form is RemoveElseForm.TRANSFORMED
            ):
                # Remove else and move its body after the if statement
                assert match.else_block is not None

                if_without_else = match.if_node.with_changes(orelse=None)
                new_body.append(if_without_else)
                new_body.extend(match.else_block.body)
                i += 1
                continue

            # ---------- TRANSFORMED (without else) -> ORIGINAL (with else) ----------
            if (
                match.form is RemoveElseForm.TRANSFORMED
                and target_form is RemoveElseForm.ORIGINAL
            ):
                # Simplified strategy: absorb all following statements after the current if into the else block
                following = body[i + 1 :]
                else_block = cst.IndentedBlock(body=following or [])

                new_if = match.if_node.with_changes(
                    orelse=cst.Else(body=else_block)
                )
                new_body.append(new_if)
                # All following statements have been used as the else body, so this block ends here
                i = n
                continue

            # Other cases should not occur in theory; keep unchanged as a fallback
            new_body.append(stmt)
            i += 1

        return updated_node.with_changes(body=new_body)
