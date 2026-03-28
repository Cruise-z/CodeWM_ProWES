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

# Map string variant keys to concrete forms
_VARIANT_KEY_TO_FORM: dict[str, ForListCompForm] = {
    # loop-based form
    "loop": ForListCompForm.LOOP_BASED,
    "loop_based": ForListCompForm.LOOP_BASED,
    "for_loop": ForListCompForm.LOOP_BASED,

    # comprehension form
    "comprehension": ForListCompForm.COMPREHENSION_BASED,
    "listcomp": ForListCompForm.COMPREHENSION_BASED,
    "list_comprehension": ForListCompForm.COMPREHENSION_BASED,
}


@register_rule
class ForToListComprehensionRule(BaseRule):
    """
    Multi-variant rule:

    LOOP_BASED form:
        cubes = []
        for i in range(20):
            cubes.append(i**3)

    COMPREHENSION_BASED form:
        cubes = [i**3 for i in range(20)]

    Direction rules, based on the new RuleDirection:

      - direction.mode == "AUTO":
            LOOP_BASED            -> COMPREHENSION_BASED
            COMPREHENSION_BASED   -> LOOP_BASED

      - direction.mode == "TO_VARIANT":
            direction.variant is a string key:
                "loop" / "loop_based" / "for_loop"
                "comprehension" / "listcomp" / "list_comprehension"
            This rule maps those keys to ForListCompForm:
                - if the current form is already the target form, no rewrite is performed;
                - otherwise it converts between the two forms accordingly.
    """

    rule_id = "refactoring.for_to_list_comprehension"
    description = "for loop <-> list comprehension"

    # Declare the variant names supported by this rule, mainly for docs/CLI
    variants = ("loop", "comprehension")

    # ------- Determine the target form from direction -------

    def _target_form_for(self, match: ForListCompMatch) -> Optional[ForListCompForm]:
        cur = match.form
        direction = self.direction

        # AUTO: swap between the two forms
        if direction.mode == "AUTO":
            if cur is ForListCompForm.LOOP_BASED:
                target = ForListCompForm.COMPREHENSION_BASED
            elif cur is ForListCompForm.COMPREHENSION_BASED:
                target = ForListCompForm.LOOP_BASED
            else:
                return None

        # TO_VARIANT: determine the target form from the variant string
        elif direction.mode == "TO_VARIANT":
            key = direction.variant
            if key is None:
                return None
            form = _VARIANT_KEY_TO_FORM.get(key.lower())
            if form is None:
                # Unknown key: do not rewrite for safety
                return None
            target = form

        else:
            # Unknown mode: do not rewrite
            return None

        # Do not rewrite if the current form already matches the target
        if target is cur:
            return None

        return target

    # ------- Main rewrite logic: handle assign + for pairs inside indented blocks -------

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

            # This rule did not match, so keep the statement unchanged
            if match is None:
                new_body.append(stmt)
                i += 1
                continue

            # Determine the target form from the current form and direction
            target_form = self._target_form_for(match)
            if target_form is None:
                # No rewrite needed, keep as-is
                new_body.append(stmt)
                i += 1
                continue

            # ---------- LOOP_BASED -> COMPREHENSION_BASED ----------
            if (
                match.form is ForListCompForm.LOOP_BASED
                and target_form is ForListCompForm.COMPREHENSION_BASED
            ):
                # Build a list-comprehension assignment to replace the original assign + for statement pair
                new_assign = _build_comprehension_assign(match)
                new_body.append(new_assign)
                # Skip the for statement
                i += 2
                continue

            # ---------- COMPREHENSION_BASED -> LOOP_BASED ----------
            if (
                match.form is ForListCompForm.COMPREHENSION_BASED
                and target_form is ForListCompForm.LOOP_BASED
            ):
                # Split a list-comprehension assignment into assign [] + for ... append(...)
                init_assign, for_stmt = _build_loop_from_comprehension(match)
                new_body.append(init_assign)
                new_body.append(for_stmt)
                i += 1
                continue

            # Other cases should not happen in theory; keep the original form as a fallback
            new_body.append(stmt)
            i += 1

        return updated_node.with_changes(body=new_body)


# ------- Helper constructors -------


def _build_comprehension_assign(match: ForListCompMatch) -> cst.SimpleStatementLine:
    """
    Build from a LOOP_BASED match:

        cubes = [value_expr for index_name in iter_expr]
    """
    # Keep the original assignment, including target and related parts, and only replace the value
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
    Build from a COMPREHENSION_BASED match:

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
