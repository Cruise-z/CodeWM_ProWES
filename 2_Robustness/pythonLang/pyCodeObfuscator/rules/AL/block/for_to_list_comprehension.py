# pyCodeObfuscator/rules/AL/block/for_to_list_comprehension.py
from __future__ import annotations

from typing import List, Optional, Tuple

import libcst as cst

from ....core.rule_base import BaseRule, RuleDirection, register_rule
from ....patterns.AL.block.for_to_list_comprehension_pattern import (
    match_for_list_comprehension_pair,
    ForListCompForm,
    ForListCompMatch,
)

# 将字符串 variant key 映射到具体形态
_VARIANT_KEY_TO_FORM: dict[str, ForListCompForm] = {
    # loop-based 形态
    "loop": ForListCompForm.LOOP_BASED,
    "loop_based": ForListCompForm.LOOP_BASED,
    "for_loop": ForListCompForm.LOOP_BASED,

    # comprehension 形态
    "comprehension": ForListCompForm.COMPREHENSION_BASED,
    "listcomp": ForListCompForm.COMPREHENSION_BASED,
    "list_comprehension": ForListCompForm.COMPREHENSION_BASED,
}


@register_rule
class ForToListComprehensionRule(BaseRule):
    """
    多形态规则：

    LOOP_BASED 形态：
        cubes = []
        for i in range(20):
            cubes.append(i**3)

    COMPREHENSION_BASED 形态：
        cubes = [i**3 for i in range(20)]

    方向约定（基于新的 RuleDirection）：

      - direction.mode == "AUTO":
            LOOP_BASED            -> COMPREHENSION_BASED
            COMPREHENSION_BASED   -> LOOP_BASED

      - direction.mode == "TO_VARIANT":
            direction.variant 为字符串 key：
                "loop" / "loop_based" / "for_loop"
                "comprehension" / "listcomp" / "list_comprehension"
            本规则将这些 key 映射到 ForListCompForm：
                - 如果当前就是目标形态，则不改写；
                - 否则在两种形态之间做对应转换。
    """

    rule_id = "refactoring.for_to_list_comprehension"
    description = "for 循环 <-> 列表推导式"

    # 声明本规则支持的变体名称（主要用于文档/CLI）
    variants = ("loop", "comprehension")

    # ------- 根据 direction 决定目标形态 -------

    def _target_form_for(self, match: ForListCompMatch) -> Optional[ForListCompForm]:
        cur = match.form
        direction = self.direction

        # AUTO：两种形态互换
        if direction.mode == "AUTO":
            if cur is ForListCompForm.LOOP_BASED:
                target = ForListCompForm.COMPREHENSION_BASED
            elif cur is ForListCompForm.COMPREHENSION_BASED:
                target = ForListCompForm.LOOP_BASED
            else:
                return None

        # TO_VARIANT：根据 variant 字符串决定目标形态
        elif direction.mode == "TO_VARIANT":
            key = direction.variant
            if key is None:
                return None
            form = _VARIANT_KEY_TO_FORM.get(key.lower())
            if form is None:
                # 不认识的 key：安全起见不改写
                return None
            target = form

        else:
            # 未知 mode：不改写
            return None

        # 如果当前形态已经是目标形态，则不改写
        if target is cur:
            return None

        return target

    # ------- 主重写逻辑：在缩进块中成对处理 assign + for -------

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
            next_stmt: Optional[cst.BaseStatement] = body[i + 1] if i + 1 < n else None

            match = match_for_list_comprehension_pair(stmt, next_stmt)

            # 未命中这条规则，直接保留
            if match is None:
                new_body.append(stmt)
                i += 1
                continue

            # 根据当前形态 + direction 决定目标形态
            target_form = self._target_form_for(match)
            if target_form is None:
                # 不需要改写，原样保留
                new_body.append(stmt)
                i += 1
                continue

            # ---------- LOOP_BASED -> COMPREHENSION_BASED ----------
            if (
                match.form is ForListCompForm.LOOP_BASED
                and target_form is ForListCompForm.COMPREHENSION_BASED
            ):
                # 构造一条列表推导赋值，替换原来的 assign + for 两条语句
                new_assign = _build_comprehension_assign(match)
                new_body.append(new_assign)
                # 跳过 for 语句
                i += 2
                continue

            # ---------- COMPREHENSION_BASED -> LOOP_BASED ----------
            if (
                match.form is ForListCompForm.COMPREHENSION_BASED
                and target_form is ForListCompForm.LOOP_BASED
            ):
                # 把一条列表推导赋值拆成 assign [] + for ... append(...)
                init_assign, for_stmt = _build_loop_from_comprehension(match)
                new_body.append(init_assign)
                new_body.append(for_stmt)
                i += 1
                continue

            # 其它情况理论上不会发生，兜底保留原样
            new_body.append(stmt)
            i += 1

        return updated_node.with_changes(body=new_body)


# ------- 辅助构造函数 -------


def _build_comprehension_assign(match: ForListCompMatch) -> cst.SimpleStatementLine:
    """
    根据 LOOP_BASED 匹配结果构造：

        cubes = [value_expr for index_name in iter_expr]
    """
    # 保留原 assign（target 等），只改 value
    assign = _extract_single_assign_from_stmt(match.assign_stmt)
    assert assign is not None

    comp_for = cst.CompFor(
        target=cst.Name(match.index_name),
        iter=match.iter_expr,
    )

    list_comp = cst.ListComp(
        elt=match.value_expr,
        for_in=comp_for,
    )

    new_assign = assign.with_changes(value=list_comp)
    return match.assign_stmt.with_changes(body=[new_assign])


def _build_loop_from_comprehension(
    match: ForListCompMatch,
) -> Tuple[cst.SimpleStatementLine, cst.For]:
    """
    根据 COMPREHENSION_BASED 匹配结果构造：

        cubes = []
        for i in iter_expr:
            cubes.append(value_expr)
    """
    assign = _extract_single_assign_from_stmt(match.assign_stmt)
    assert assign is not None

    # 1) cubes = []
    empty_list = cst.List(elements=[])
    new_assign = assign.with_changes(value=empty_list)
    init_assign_stmt = match.assign_stmt.with_changes(body=[new_assign])

    # 2) for i in iter_expr:
    #        cubes.append(value_expr)
    append_call = cst.Call(
        func=cst.Attribute(
            value=cst.Name(match.target_name),
            attr=cst.Name("append"),
        ),
        args=[cst.Arg(value=match.value_expr)],
    )
    body_stmt = cst.SimpleStatementLine(body=[cst.Expr(value=append_call)])
    for_stmt = cst.For(
        target=cst.Name(match.index_name),
        iter=match.iter_expr,
        body=cst.IndentedBlock(body=[body_stmt]),
    )

    return init_assign_stmt, for_stmt


def _extract_single_assign_from_stmt(
    stmt: cst.BaseStatement,
) -> Optional[cst.Assign]:
    if not isinstance(stmt, cst.SimpleStatementLine):
        return None
    if len(stmt.body) != 1:
        return None
    inner = stmt.body[0]
    if not isinstance(inner, cst.Assign):
        return None
    return inner
