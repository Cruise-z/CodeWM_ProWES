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


# 为变体字符串提供一个映射：with_else / no_else
_VARIANT_KEY_TO_FORM: dict[str, RemoveElseForm] = {
    "with_else": RemoveElseForm.ORIGINAL,     # 有 else 的形态
    "has_else": RemoveElseForm.ORIGINAL,
    "original": RemoveElseForm.ORIGINAL,

    "no_else": RemoveElseForm.TRANSFORMED,    # 去掉 else 的形态
    "without_else": RemoveElseForm.TRANSFORMED,
    "removed_else": RemoveElseForm.TRANSFORMED,
    "transformed": RemoveElseForm.TRANSFORMED,
}


@register_rule
class RemoveUnnecessaryElseRule(BaseRule):
    """
    去掉多余 else 的双形态重构：

    形态 A（ORIGINAL / with_else）：
        if cond:
            return ...
        else:
            # some code

    形态 B（TRANSFORMED / no_else）：
        if cond:
            return ...
        # some code

    方向约定（新 RuleDirection 架构）：

      - direction.mode == "AUTO":
            ORIGINAL     -> TRANSFORMED
            TRANSFORMED  -> ORIGINAL

      - direction.mode == "TO_VARIANT":
            direction.variant 为字符串 key：
                "with_else" / "has_else" / "original"
                "no_else" / "without_else" / "removed_else" / "transformed"
            本规则将这些 key 映射到 RemoveElseForm，并在两个形态之间做对应转换。
    """

    rule_id = "refactoring.remove_unnecessary_else"
    description = "Original <-> 去掉多余 else 的重构"
    variants = ("with_else", "no_else")

    # ------- 根据 direction 决定目标形态 -------

    def _target_form_for(self, match: RemoveElseMatch) -> Optional[RemoveElseForm]:
        cur = match.form
        direction = self.direction

        # AUTO：两种形态互换
        if direction.mode == "AUTO":
            if cur is RemoveElseForm.ORIGINAL:
                target = RemoveElseForm.TRANSFORMED
            elif cur is RemoveElseForm.TRANSFORMED:
                target = RemoveElseForm.ORIGINAL
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

        # 如果当前形态已经是目标形态，则不改写
        if target is cur:
            return None

        return target

    # ------- 主重写逻辑：在缩进块中处理 if/else -------

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

            # 未命中 pattern，直接保留
            if match is None:
                new_body.append(stmt)
                i += 1
                continue

            target_form = self._target_form_for(match)
            if target_form is None:
                # 当前方向不需要/不允许改写这个 if
                new_body.append(stmt)
                i += 1
                continue

            # ---------- ORIGINAL(有 else) -> TRANSFORMED(无 else) ----------
            if (
                match.form is RemoveElseForm.ORIGINAL
                and target_form is RemoveElseForm.TRANSFORMED
            ):
                # 去掉 else，else 体下沉到 if 后面
                assert match.else_block is not None

                if_without_else = match.if_node.with_changes(orelse=None)
                new_body.append(if_without_else)
                new_body.extend(match.else_block.body)
                i += 1
                continue

            # ---------- TRANSFORMED(无 else) -> ORIGINAL(有 else) ----------
            if (
                match.form is RemoveElseForm.TRANSFORMED
                and target_form is RemoveElseForm.ORIGINAL
            ):
                # 简化策略：把当前 if 后面的所有语句“吸进” else 块
                following = body[i + 1 :]
                else_block = cst.IndentedBlock(body=following or [])

                new_if = match.if_node.with_changes(
                    orelse=cst.Else(body=else_block)
                )
                new_body.append(new_if)
                # 后续语句已经全部用作 else body，这个 block 结束
                i = n
                continue

            # 其他情况（理论上不会走到），保底不改写
            new_body.append(stmt)
            i += 1

        return updated_node.with_changes(body=new_body)
