# pyCodeObfuscator/rules/AL/block/loop_index_direct_reference.py
from __future__ import annotations

from typing import Optional

import libcst as cst

from ....core.rule_base import BaseRule, RuleDirection, register_rule
from ....patterns.AL.block.loop_index_direct_reference_pattern import (
    match_loop_index_direct_reference,
    LoopIndexForm,
    LoopIndexDirectReferenceMatch,
)


def _make_element_name(list_name: str) -> str:
    """
    根据列表名猜一个元素变量名，用于:
        currencies -> currency
        users      -> user
        默认: xxx -> xxx_item
    """
    if list_name.endswith("ies") and len(list_name) > 3:
        return list_name[:-3] + "y"
    if list_name.endswith("s") and len(list_name) > 1:
        return list_name[:-1]
    return list_name + "_item"


class _IndexToElementReplacer(cst.CSTTransformer):
    """
    把 list[i] 替换为 element 变量。
    """

    def __init__(self, list_name: str, index_name: str, element_name: str) -> None:
        self.list_name = list_name
        self.index_name = index_name
        self.element_name = element_name

    def leave_Subscript(
        self, original_node: cst.Subscript, updated_node: cst.Subscript
    ) -> cst.BaseExpression:
        # 只处理 list_name[...] 这种下标
        if not isinstance(updated_node.value, cst.Name):
            return updated_node
        if updated_node.value.value != self.list_name:
            return updated_node

        # 只处理单一下标: list[i]
        if len(updated_node.slice) != 1:
            return updated_node

        elem = updated_node.slice[0]
        if not isinstance(elem.slice, cst.Index):
            return updated_node

        index_expr = elem.slice.value
        if isinstance(index_expr, cst.Name) and index_expr.value == self.index_name:
            # list[i] -> element_name
            return cst.Name(self.element_name)

        return updated_node


class _ElementToIndexReplacer(cst.CSTTransformer):
    """
    把 element 变量替换为 list[index]。
    """

    def __init__(self, list_name: str, index_name: str, element_name: str) -> None:
        self.list_name = list_name
        self.index_name = index_name
        self.element_name = element_name

    def leave_Name(
        self, original_node: cst.Name, updated_node: cst.Name
    ) -> cst.BaseExpression:
        # 把 element_name 替换成 list[index]
        if original_node.value != self.element_name:
            return updated_node

        return cst.Subscript(
            value=cst.Name(self.list_name),
            slice=[
                cst.SubscriptElement(
                    slice=cst.Index(
                        value=cst.Name(self.index_name),
                    )
                )
            ],
        )


class _VarAssignedFinder(cst.CSTVisitor):
    """
    检测某个变量在 body 中是否被赋值（作为赋值目标）。
    如果被赋值，则认为转换不安全。
    """

    def __init__(self, var_name: str) -> None:
        self.var_name = var_name
        self.assigned = False

    def visit_Assign(self, node: cst.Assign) -> Optional[bool]:
        for target in node.targets:
            t = target.target
            if isinstance(t, cst.Name) and t.value == self.var_name:
                self.assigned = True
                return False  # 提前停止遍历
        return None

    def visit_AugAssign(self, node: cst.AugAssign) -> Optional[bool]:
        t = node.target
        if isinstance(t, cst.Name) and t.value == self.var_name:
            self.assigned = True
            return False
        return None


# 将 variant 字符串映射到形态
_VARIANT_KEY_TO_FORM: dict[str, LoopIndexForm] = {
    # index-based 形态
    "index": LoopIndexForm.INDEX_BASED,
    "index_based": LoopIndexForm.INDEX_BASED,
    "range_len": LoopIndexForm.INDEX_BASED,

    # element-based 形态
    "element": LoopIndexForm.ELEMENT_BASED,
    "direct": LoopIndexForm.ELEMENT_BASED,
    "direct_element": LoopIndexForm.ELEMENT_BASED,
}


@register_rule
class LoopIndexDirectReferenceRule(BaseRule):
    """
    for i in range(len(currencies)):
        print(currencies[i])
    <->

    for currency in currencies:
        print(currency)

    多形态方向约定（基于 RuleDirection）：

      - direction.mode == "AUTO":
            INDEX_BASED      -> ELEMENT_BASED
            ELEMENT_BASED    -> INDEX_BASED

      - direction.mode == "TO_VARIANT":
            direction.variant 为字符串 key：
                "index" / "index_based" / "range_len"
                "element" / "direct" / "direct_element"
            本规则将这些 key 映射到 LoopIndexForm 并进行相应转换。
    """

    rule_id = "refactoring.loop_index_direct_reference"
    description = "下标访问 <-> 直接元素变量 的循环重构"

    # 声明本规则支持的变体名称（主要用于 CLI/文档）
    variants = ("index", "element")

    # ------- 根据 direction 决定目标形态 -------

    def _target_form_for(self, match: LoopIndexDirectReferenceMatch) -> Optional[LoopIndexForm]:
        cur = match.form
        direction = self.direction

        # AUTO：两种形态互换
        if direction.mode == "AUTO":
            if cur is LoopIndexForm.INDEX_BASED:
                target = LoopIndexForm.ELEMENT_BASED
            elif cur is LoopIndexForm.ELEMENT_BASED:
                target = LoopIndexForm.INDEX_BASED
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

    # ------- 主重写逻辑 -------

    def leave_For(self, original_node: cst.For, updated_node: cst.For) -> cst.For:
        match = match_loop_index_direct_reference(updated_node)
        if match is None:
            return updated_node

        target_form = self._target_form_for(match)
        if target_form is None:
            return updated_node

        # --------------- INDEX_BASED -> ELEMENT_BASED ---------------
        if (
            match.form is LoopIndexForm.INDEX_BASED
            and target_form is LoopIndexForm.ELEMENT_BASED
        ):
            return self._index_to_element(updated_node, match)

        # --------------- ELEMENT_BASED -> INDEX_BASED ---------------
        if (
            match.form is LoopIndexForm.ELEMENT_BASED
            and target_form is LoopIndexForm.INDEX_BASED
        ):
            return self._element_to_index(updated_node, match)

        # 兜底：保持不变
        return updated_node

    # --------------- 方向 1: INDEX_BASED -> ELEMENT_BASED ---------------

    def _index_to_element(
        self, node: cst.For, match: LoopIndexDirectReferenceMatch
    ) -> cst.For:
        assert match.index_name is not None

        list_name = match.list_name
        index_name = match.index_name
        # 如果 pattern 没给出 element_name，就根据 list_name 猜一个
        element_name = match.element_name or _make_element_name(list_name)

        replacer = _IndexToElementReplacer(
            list_name=list_name,
            index_name=index_name,
            element_name=element_name,
        )
        new_body = node.body.visit(replacer)

        return node.with_changes(
            target=cst.Name(element_name),
            iter=cst.Name(list_name),
            body=new_body,
        )

    # --------------- 方向 2: ELEMENT_BASED -> INDEX_BASED ---------------

    def _element_to_index(
        self, node: cst.For, match: LoopIndexDirectReferenceMatch
    ) -> cst.For:
        assert match.element_name is not None

        list_name = match.list_name
        element_name = match.element_name
        index_name = f"{element_name}_idx"

        # 如果 element 变量在 body 中被赋值，转换可能改变语义，保守起见跳过
        finder = _VarAssignedFinder(element_name)
        node.body.visit(finder)
        if finder.assigned:
            return node

        replacer = _ElementToIndexReplacer(
            list_name=list_name,
            index_name=index_name,
            element_name=element_name,
        )
        new_body = node.body.visit(replacer)

        # 构造 range(len(list_name))
        new_iter = cst.Call(
            func=cst.Name("range"),
            args=[
                cst.Arg(
                    value=cst.Call(
                        func=cst.Name("len"),
                        args=[cst.Arg(value=cst.Name(list_name))],
                    )
                )
            ],
        )

        return node.with_changes(
            target=cst.Name(index_name),
            iter=new_iter,
            body=new_body,
        )
