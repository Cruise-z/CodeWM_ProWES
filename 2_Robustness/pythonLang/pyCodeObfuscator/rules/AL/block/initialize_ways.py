# pyCodeObfuscator/rules/AL/block/initialize_ways.py
from __future__ import annotations

from typing import Dict, List, Optional

import libcst as cst

from ....core.rule_base import BaseRule, RuleDirection, register_rule
from ....patterns.AL.block.initialize_ways_pattern import (
    InitializeWaysForm,
    InitializeWaysMatch,
    match_initialize_ways_single,
    match_initialize_ways_pair,
)


# Map variant names to forms
_VARIANT_KEY_TO_FORM: Dict[str, InitializeWaysForm] = {
    "dict_call": InitializeWaysForm.DICT_CALL,
    "dict": InitializeWaysForm.DICT_CALL,
    "call": InitializeWaysForm.DICT_CALL,
    "empty_subscript": InitializeWaysForm.EMPTY_THEN_SUBSCRIPT,
    "subscript": InitializeWaysForm.EMPTY_THEN_SUBSCRIPT,
    "two_step": InitializeWaysForm.EMPTY_THEN_SUBSCRIPT,
}


def _rewrite_dict_call_to_empty_subscript(
    match: InitializeWaysMatch,
) -> List[cst.BaseStatement]:
    """
    d = dict(name="1", age=2)
    =>
    d = {}
    d["name"] = "1"
    d["age"] = 2
    """
    call = match.call
    if call is None:
        # Defensive fallback: this should not happen, so keep the original form
        return [match.first_stmt]

    target = match.target

    # Build the line d = {}
    empty_assign = cst.Assign(
        targets=[cst.AssignTarget(target=target)],
        value=cst.Dict([]),
    )
    empty_stmt = match.first_stmt.with_changes(body=[empty_assign])

    # Then turn each keyword into a statement like d["key"] = value
    subscript_stmts: List[cst.SimpleStatementLine] = []

    for arg in call.args:
        if arg.keyword is None:
            # If positional arguments or **kwargs exist, abort rewriting and return the original statement
            return [match.first_stmt]

        kw_name = arg.keyword.value  # for example "name"
        key_expr = cst.SimpleString(repr(kw_name))

        subscript = cst.Subscript(
            value=target,
            slice=[
                cst.SubscriptElement(
                    slice=cst.Index(value=key_expr),
                )
            ],
        )
        assign = cst.Assign(
            targets=[cst.AssignTarget(target=subscript)],
            value=arg.value,
        )
        sub_stmt = match.first_stmt.with_changes(body=[assign])
        subscript_stmts.append(sub_stmt)

    return [empty_stmt, *subscript_stmts]


def _rewrite_empty_subscript_to_dict_call(
    match: InitializeWaysMatch,
) -> List[cst.BaseStatement]:
    """
    d = {}
    d["name"] = "1"
    =>
    d = dict(name="1")
    """
    if not match.keys or not match.values or match.second_stmt is None:
        # Incomplete match, keep the original form
        return [match.first_stmt, match.second_stmt] if match.second_stmt else [match.first_stmt]

    target = match.target
    key_expr = match.keys[0]
    value_expr = match.values[0]

    # Only accept simple literal keys like d["name"], so they can be safely restored as keywords
    if not isinstance(key_expr, cst.SimpleString):
        return [match.first_stmt, match.second_stmt]

    raw = key_expr.value  # quoted string literal, for example "'name'" or "\"name\""
    if len(raw) < 2 or raw[0] not in ("'", '"') or raw[-1] != raw[0]:
        return [match.first_stmt, match.second_stmt]

    ident = raw[1:-1]  # strip the leading and trailing quotes
    if not ident.isidentifier():
        return [match.first_stmt, match.second_stmt]

    call = cst.Call(
        func=cst.Name("dict"),
        args=[cst.Arg(keyword=cst.Name(ident), value=value_expr)],
    )
    assign = cst.Assign(
        targets=[cst.AssignTarget(target=target)],
        value=call,
    )

    new_stmt = match.first_stmt.with_changes(body=[assign])
    return [new_stmt]


@register_rule
class InitializeWaysRule(BaseRule):
    """
    Refactoring: Initialize ways.

    Convert between the following two initialization styles:
      - d = dict(name="1")
      - d = {}; d["name"] = "1"

    This is a block-level rule that recognizes and rewrites adjacent statements inside a statement list.
    """

    rule_id = "refactoring.initialize_ways"
    description = (
        "Refactor between `d = dict(...)` and `d = {}; d[<key>] = ...` "
        "initialization styles."
    )
    variants = ("dict_call", "empty_subscript")

    def _target_form_for(
        self, current: InitializeWaysForm
    ) -> Optional[InitializeWaysForm]:
        """
        Determine the target form from the current form and RuleDirection.
        Return None to indicate that no rewrite is needed.
        """
        direction = self.direction

        if direction.mode == "AUTO":
            # AUTO: flip between the two forms
            if current is InitializeWaysForm.DICT_CALL:
                target = InitializeWaysForm.EMPTY_THEN_SUBSCRIPT
            elif current is InitializeWaysForm.EMPTY_THEN_SUBSCRIPT:
                target = InitializeWaysForm.DICT_CALL
            else:
                return None

        elif direction.mode == "TO_VARIANT":
            key = direction.variant
            if key is None:
                return None
            form = _VARIANT_KEY_TO_FORM.get(key.lower())
            if form is None:
                return None
            target = form

        else:
            return None

        if target is current:
            return None
        return target

    # --------------------------
    # Shared helper for block rewriting
    # --------------------------

    def _rewrite_block_body(
        self,
        body: List[cst.BaseStatement],
    ) -> List[cst.BaseStatement]:
        """
        Scan a statement list and rewrite Initialize ways patterns.
        """
        new_body: List[cst.BaseStatement] = []
        i = 0
        n = len(body)

        while i < n:
            stmt = body[i]

            # Apply this rule only on SimpleStatementLine
            if isinstance(stmt, cst.SimpleStatementLine):
                # Prefer trying the two-line pattern first: d = {}; d["name"] = "1"
                pair_match: Optional[InitializeWaysMatch] = None
                if i + 1 < n and isinstance(body[i + 1], cst.SimpleStatementLine):
                    pair_match = match_initialize_ways_pair(stmt, body[i + 1])

                if pair_match is not None:
                    target_form = self._target_form_for(pair_match.form)
                    if target_form is not None:
                        if (
                            pair_match.form is InitializeWaysForm.EMPTY_THEN_SUBSCRIPT
                            and target_form is InitializeWaysForm.DICT_CALL
                        ):
                            replaced = _rewrite_empty_subscript_to_dict_call(pair_match)
                            new_body.extend(replaced)
                            i += 2
                            continue
                    # No rewrite needed, so keep it unchanged
                    new_body.append(stmt)
                    i += 1
                    continue

                # Single-line pattern: d = dict(name="1")
                single_match = match_initialize_ways_single(stmt)
                if single_match is not None:
                    target_form = self._target_form_for(single_match.form)
                    if target_form is not None:
                        if (
                            single_match.form is InitializeWaysForm.DICT_CALL
                            and target_form is InitializeWaysForm.EMPTY_THEN_SUBSCRIPT
                        ):
                            replaced = _rewrite_dict_call_to_empty_subscript(single_match)
                            new_body.extend(replaced)
                            i += 1
                            continue

            # Default case: rule does not trigger, keep as-is
            new_body.append(stmt)
            i += 1

        return new_body

    # --------------------------
    # Rewrites for different block node types
    # --------------------------

    def leave_Module(
        self,
        original_node: cst.Module,
        updated_node: cst.Module,
    ) -> cst.Module:
        new_body = self._rewrite_block_body(list(updated_node.body))
        return updated_node.with_changes(body=new_body)

    def leave_IndentedBlock(
        self,
        original_node: cst.IndentedBlock,
        updated_node: cst.IndentedBlock,
    ) -> cst.IndentedBlock:
        new_body = self._rewrite_block_body(list(updated_node.body))
        return updated_node.with_changes(body=new_body)

    def leave_SimpleStatementSuite(
        self,
        original_node: cst.SimpleStatementSuite,
        updated_node: cst.SimpleStatementSuite,
    ) -> cst.SimpleStatementSuite:
        new_body = self._rewrite_block_body(list(updated_node.body))
        return updated_node.with_changes(body=new_body)
