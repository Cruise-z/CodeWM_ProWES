# pyCodeObfuscator/patterns/AL/block/unnecessary_else_pattern.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import libcst as cst


class RemoveElseForm(str, Enum):
    ORIGINAL = "original"
    TRANSFORMED = "transformed"


@dataclass
class RemoveElseMatch:
    """
    Match information for the "remove unnecessary else" rule.

    form:
        - ORIGINAL:  current form is original
        - TRANSFORMED: current form is transformed

    if_node:    matched if statement node
    then_block: code block for the if branch
    else_block: if the current form is ORIGINAL, this is the else block; otherwise None
    """
    form: RemoveElseForm
    if_node: cst.If
    then_block: cst.IndentedBlock
    else_block: Optional[cst.IndentedBlock] = None


def block_ends_with_early_exit(block: cst.IndentedBlock) -> bool:
    """
    Check whether the last statement in an indented block is return / raise / break / continue,
    which is the necessary condition for safely removing else.
    """
    if not block.body:
        return False

    last_stmt = block.body[-1]
    if not isinstance(last_stmt, cst.SimpleStatementLine):
        return False
    if len(last_stmt.body) != 1:
        return False

    small = last_stmt.body[0]
    return isinstance(
        small,
        (cst.Return, cst.Raise, cst.Break, cst.Continue),
    )


def match_remove_unnecessary_else(node: cst.CSTNode) -> Optional[RemoveElseMatch]:
    """
    Try to match the unnecessary-else pattern on a single node.

    Return RemoveElseMatch when one of the two forms matches:
        - form == ORIGINAL:    if has an else block and then_block exits early
        - form == TRANSFORMED: if has no else block and then_block exits early

    Return None in all other cases.
    """
    if not isinstance(node, cst.If):
        return None

    # Case 1: original form
    if node.orelse is not None:
        if not isinstance(node.body, cst.IndentedBlock):
            return None
        if not isinstance(node.orelse.body, cst.IndentedBlock):
            return None
        if not block_ends_with_early_exit(node.body):
            return None

        return RemoveElseMatch(
            form=RemoveElseForm.ORIGINAL,
            if_node=node,
            then_block=node.body,
            else_block=node.orelse.body,
        )

    # Case 2: transformed form
    if node.orelse is None:
        if not isinstance(node.body, cst.IndentedBlock):
            return None
        if not block_ends_with_early_exit(node.body):
            return None

        return RemoveElseMatch(
            form=RemoveElseForm.TRANSFORMED,
            if_node=node,
            then_block=node.body,
            else_block=None,
        )

    return None
