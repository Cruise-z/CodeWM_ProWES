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
    Guess an element variable name from the list name, for example:
        currencies -> currency
        users      -> user
        Default: xxx -> xxx_item
    """
    if list_name.endswith("ies") and len(list_name) > 3:
        return list_name[:-3] + "y"
    if list_name.endswith("s") and len(list_name) > 1:
        return list_name[:-1]
    return list_name + "_item"


class _IndexToElementReplacer(cst.CSTTransformer):
    """
    Replace `list[i]` with an element variable.
    """

    def __init__(self, list_name: str, index_name: str, element_name: str) -> None:
        self.list_name = list_name
        self.index_name = index_name
        self.element_name = element_name

    def leave_Subscript(
        self, original_node: cst.Subscript, updated_node: cst.Subscript
    ) -> cst.BaseExpression:
        # Only handle subscripts of the form list_name[...]
        if not isinstance(updated_node.value, cst.Name):
            return updated_node
        if updated_node.value.value != self.list_name:
            return updated_node

        # Only handle a single index: list[i]
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
    Replace the element variable with `list[index]`.
    """

    def __init__(self, list_name: str, index_name: str, element_name: str) -> None:
        self.list_name = list_name
        self.index_name = index_name
        self.element_name = element_name

    def leave_Name(
        self, original_node: cst.Name, updated_node: cst.Name
    ) -> cst.BaseExpression:
        # Replace element_name with list[index]
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
    Detect whether a variable is assigned inside the loop body.
    If it is assigned, treat the transformation as unsafe.
    """

    def __init__(self, var_name: str) -> None:
        self.var_name = var_name
        self.assigned = False

    def visit_Assign(self, node: cst.Assign) -> Optional[bool]:
        for target in node.targets:
            t = target.target
            if isinstance(t, cst.Name) and t.value == self.var_name:
                self.assigned = True
                return False  # Stop traversal early
        return None

    def visit_AugAssign(self, node: cst.AugAssign) -> Optional[bool]:
        t = node.target
        if isinstance(t, cst.Name) and t.value == self.var_name:
            self.assigned = True
            return False
        return None


# Map variant strings to forms
_VARIANT_KEY_TO_FORM: dict[str, LoopIndexForm] = {
    # index-based form
    "index": LoopIndexForm.INDEX_BASED,
    "index_based": LoopIndexForm.INDEX_BASED,
    "range_len": LoopIndexForm.INDEX_BASED,

    # element-based form
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

    Multi-variant direction rules (based on RuleDirection):

      - direction.mode == "AUTO":
            INDEX_BASED      -> ELEMENT_BASED
            ELEMENT_BASED    -> INDEX_BASED

      - direction.mode == "TO_VARIANT":
            direction.variant is a string key:
                "index" / "index_based" / "range_len"
                "element" / "direct" / "direct_element"
            This rule maps those keys to LoopIndexForm and performs the corresponding conversion.
    """

    rule_id = "refactoring.loop_index_direct_reference"
    description = "Loop refactor: indexed access <-> direct element variable"

    # Declare the variant names supported by this rule (mainly for CLI/docs)
    variants = ("index", "element")

    # ------- Determine the target form from direction -------

    def _target_form_for(self, match: LoopIndexDirectReferenceMatch) -> Optional[LoopIndexForm]:
        cur = match.form
        direction = self.direction

        # AUTO: swap between the two forms
        if direction.mode == "AUTO":
            if cur is LoopIndexForm.INDEX_BASED:
                target = LoopIndexForm.ELEMENT_BASED
            elif cur is LoopIndexForm.ELEMENT_BASED:
                target = LoopIndexForm.INDEX_BASED
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

    # ------- Main rewrite logic -------

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

        # Fallback: keep unchanged
        return updated_node

    # --------------- Direction 1: INDEX_BASED -> ELEMENT_BASED ---------------

    def _index_to_element(
        self, node: cst.For, match: LoopIndexDirectReferenceMatch
    ) -> cst.For:
        assert match.index_name is not None

        list_name = match.list_name
        index_name = match.index_name
        # If the pattern does not provide element_name, infer one from list_name
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

    # --------------- Direction 2: ELEMENT_BASED -> INDEX_BASED ---------------

    def _element_to_index(
        self, node: cst.For, match: LoopIndexDirectReferenceMatch
    ) -> cst.For:
        assert match.element_name is not None

        list_name = match.list_name
        element_name = match.element_name
        index_name = f"{element_name}_idx"

        # If the element variable is assigned in the body, the transform may change semantics, so skip it conservatively
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

        # Build range(len(list_name))
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
