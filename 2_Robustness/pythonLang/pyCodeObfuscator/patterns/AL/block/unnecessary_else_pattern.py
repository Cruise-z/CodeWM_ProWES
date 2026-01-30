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
    匹配到“去除多余 else”规则的命中信息。

    form:
        - ORIGINAL:  当前是 original 形态
        - TRANSFORMED: 当前是 transformed 形态

    if_node:    命中的 if 语句节点
    then_block: if 分支的代码块
    else_block: 如果当前是 ORIGINAL，会是 else 的代码块；否则为 None
    """
    form: RemoveElseForm
    if_node: cst.If
    then_block: cst.IndentedBlock
    else_block: Optional[cst.IndentedBlock] = None


def block_ends_with_early_exit(block: cst.IndentedBlock) -> bool:
    """
    判断一个缩进块最后一条语句是否为 return / raise / break / continue，
    作为“可以安全去掉 else”的必要条件。
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
    在单个节点上尝试匹配“多余 else”模式。

    命中两种形态之一时，返回 RemoveElseMatch：
        - form == ORIGINAL:    if 有 else，且 then_block 早退
        - form == TRANSFORMED: if 无 else，且 then_block 早退

    其它情况返回 None。
    """
    if not isinstance(node, cst.If):
        return None

    # 情形 1：original 形态
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

    # 情形 2：transformed 形态
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
