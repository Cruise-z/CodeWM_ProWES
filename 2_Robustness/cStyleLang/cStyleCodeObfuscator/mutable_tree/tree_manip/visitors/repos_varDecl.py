#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
repos_varDecl.py

A combination visitor that repositions variable declarations in C-style language ASTs.
- var_init.py
- var_pos.py
- var_same_type.py

Author: Cruise-z <cruise.zrz@gmail.com>
Affiliation: IIE CAS
Date: 2025-10-28
"""
import random
from typing import Optional, List, Dict, Tuple, Set, cast

from .visitor import TransformingVisitor
from ...nodes import (
    Node,
    Statement,
    StatementList,
    LocalVariableDeclaration,
    Declarator,
    VariableDeclarator,
    InitializingDeclarator,
    FunctionDeclarator,
    Identifier,
    ExpressionStatement,
    AssignmentExpression,
    AssignmentOps,
    node_factory,
)


def get_identifier_from_declarator(node: Declarator) -> Identifier:
    # Reuse the identifier-extraction logic you provided earlier
    if isinstance(node, VariableDeclarator):
        return node.decl_id
    else:
        return get_identifier_from_declarator(node.declarator)


def get_all_identifiers(node: Node) -> List[str]:
    # Reuse the var_pos-style identifier collection logic unchanged for maximum reuse
    ids: List[str] = []

    def _walk(n: Node):
        if isinstance(n, Identifier):
            ids.append(n.name)
        else:
            for attr in n.get_children_names():
                ch = n.get_child_at(attr)
                if ch is None:
                    continue
                _walk(ch)

    _walk(node)
    return ids


def _match_simple_assign_to_var(stmt: Statement, var_name: str):
    """
    If stmt is a simple assignment like 'var_name = <rhs>;', return rhs; otherwise return None.
    """
    if isinstance(stmt, ExpressionStatement) and isinstance(stmt.expr, AssignmentExpression):
        assign = stmt.expr
        if assign.op == AssignmentOps.EQUAL and isinstance(assign.left, Identifier):
            if assign.left.name == var_name:
                return assign.right
    return None


class ReposVarDeclVisitor(TransformingVisitor):
    """
    For a StatementList:
      1) Find the declaration position and first-use position of every variable v
      2) Then handle the declaration of v case by case:
         - If declaration and initialization happen together (declaration position == first-use position):
             (a) If other same-typed declarators remain in that LocalVariableDeclaration:
                 Split v's declaration/initialization, place 'v = init;' as an assignment after the original statement,
                 and randomly move the declaration without initialization to any slot in [block start .. before init position]
             (b) If no other same-typed declarators remain:
                 Remove the initialized declaration, place 'v = init;' after it,
                 and randomly move the declaration without initialization to any slot in [block start .. before init position]
         - If declaration and first use happen at different positions:
             (a) If other same-typed declarators remain: randomly choose one:
                 - move the declaration without initialization to any slot before first use, excluding the original slot
                 - or merge it with the first use if the first use is 'v = rhs;', replacing it with 'T v = rhs;'
             (b) If no other same-typed declarators remain: same two choices apply
      Note: if no candidate slot remains after excluding the original slot, fall back to the original slot.
    """

    def __init__(self, seed: Optional[int] = None, prefer_merge_prob: float = 0.5):
        super().__init__()
        self._rng = random.Random(seed)
        self._prefer_merge_prob = prefer_merge_prob  # Controls the "move vs merge" probability for case 3.*

    def visit_StatementList(
        self,
        node: StatementList,
        parent: Optional[Node] = None,
        parent_attr: Optional[str] = None,
    ):
        # === Phase 0: collect the original statement sequence (without modifying it yet)
        original: List[Statement] = []
        for attr in node.get_children_names():
            ch = node.get_child_at(attr)
            if ch is None:
                continue
            original.append(cast(Statement, ch))
        N = len(original)

        # === Phase 1: collect declaration information for all variables
        # name -> (decl_idx, decl_stmt: LocalVariableDeclaration, declarator, has_init, init_value_if_any, type_node, multi_in_stmt)
        VarInfo = Tuple[int, LocalVariableDeclaration, Declarator, bool, Optional[Node], Node, bool]
        var_info: Dict[str, VarInfo] = {}
        # Record all variable names in each LocalVariableDeclaration so we can tell whether sibling declarators remain
        decl_stmt_vars: Dict[int, List[str]] = {}

        for idx, stmt in enumerate(original):
            if not isinstance(stmt, LocalVariableDeclaration):
                continue

            all_decls = stmt.declarators.node_list  # All declarators in this declaration statement
            names_in_stmt: List[str] = []
            for d in all_decls:
                # tree-sitter sometimes recognizes the initializer as FunctionDeclarator; keep treating it as initialized as in the original script
                has_init = isinstance(d, InitializingDeclarator) or isinstance(d, FunctionDeclarator)
                ident = get_identifier_from_declarator(d)
                vname = ident.name
                names_in_stmt.append(vname)
                init_val = d.value if isinstance(d, InitializingDeclarator) else None
                var_info[vname] = (
                    idx,                # decl_idx
                    stmt,               # decl_stmt
                    d,                  # declarator
                    has_init,           # has_init
                    init_val,           # init value (if any)
                    stmt.type,          # type node
                    len(all_decls) > 1  # multi_in_stmt
                )
            decl_stmt_vars[idx] = names_in_stmt

        # === Phase 2: compute first-use positions
        first_use_idx: Dict[str, int] = {}
        for name, (decl_idx, _decl_stmt, _declarator, has_init, _init_val, _type_node, _multi) in var_info.items():
            if has_init:
                # Declaration with initialization: first use equals declaration position
                first_use_idx[name] = decl_idx
            else:
                # Search for the first occurrence after the declaration
                found = None
                for j in range(decl_idx + 1, N):
                    if name in get_all_identifiers(original[j]):
                        found = j
                        break
                if found is not None:
                    first_use_idx[name] = found
                else:
                    # If no use is found, treat it as unused and set first_use to the block end
                    first_use_idx[name] = N

        # === Phase 3: plan the edits (without mutating the AST yet)
        # 3.1 Variables to remove from their original declaration statements
        to_remove_from_decl: Dict[int, Set[str]] = {}
        # 3.2 New declaration-only statements to insert before a given slot
        inserts_at_slot: Dict[int, List[Statement]] = {i: [] for i in range(N + 1)}
        # 3.3 New statements to insert after a given statement (for split init -> assignment)
        inserts_after_stmt: Dict[int, List[Statement]] = {}
        # 3.4 Statement replacements (for merge: replace first use assignment with an initializing declaration)
        replace_stmt_at: Dict[int, Statement] = {}

        def choose_slot(upto_inclusive: int, exclude_slot: int) -> int:
            """
            Randomly choose a slot from {0..upto_inclusive}, excluding exclude_slot.
            If the candidate set is empty, fall back to exclude_slot.
            """
            if upto_inclusive < 0:
                return exclude_slot
            candidates = list(range(0, min(upto_inclusive, N) + 1))
            if exclude_slot in candidates:
                candidates.remove(exclude_slot)
            if not candidates:
                return exclude_slot
            return self._rng.choice(candidates)

        # 3.5 Plan actions for each variable
        for name, (decl_idx, decl_stmt, declarator, has_init, init_val, type_node, multi_in_stmt) in var_info.items():
            fidx = first_use_idx[name]  # First use (or N = end of block)
            original_slot = decl_idx     # Original declaration insertion slot (before that statement)

            # Case A: declaration with initialization (decl == first use)
            if has_init and fidx == decl_idx:
                # Split into "declaration + assignment", placing the assignment after the original statement
                # Assignment statement
                ident = get_identifier_from_declarator(declarator)
                if isinstance(declarator, InitializingDeclarator):
                    rhs = init_val
                else:
                    # FunctionDeclarator special case: no explicit value; skip splitting to avoid incomplete rhs construction
                    # Skip directly (or change to declaration-only movement if desired)
                    continue

                assign_expr = node_factory.create_assignment_expr(ident, rhs, AssignmentOps.EQUAL)
                assign_stmt = node_factory.create_expression_stmt(assign_expr)
                inserts_after_stmt.setdefault(decl_idx, []).append(assign_stmt)

                # Remove v from the original declaration
                to_remove_from_decl.setdefault(decl_idx, set()).add(name)

                # Randomly place the declaration without init somewhere before the initialization position
                # The initialization is effectively right after decl_idx, so upto = decl_idx
                # Do the same whether sibling declarators remain or not
                new_decl = node_factory.create_local_variable_declaration(
                    type_node,
                    node_factory.create_declarator_list(
                        [node_factory.create_variable_declarator(ident)]
                    ),
                )
                slot = choose_slot(decl_idx, original_slot)  # Allow decl_idx, exclude the original slot
                inserts_at_slot[slot].append(new_decl)

            # Case B: declaration and first use are at different positions
            else:
                # Two choices: merge or move (if the first use is not a simple assignment, only "move" is valid)
                do_merge = self._rng.random() < self._prefer_merge_prob
                rhs_at_use = None
                if fidx < N:
                    rhs_at_use = _match_simple_assign_to_var(original[fidx], name)

                if do_merge and (rhs_at_use is not None):
                    # Merge: replace the first-use assignment with an initializing declaration and remove v from the original declaration
                    ident = get_identifier_from_declarator(declarator)
                    init_decl = node_factory.create_initializing_declarator(
                        node_factory.create_variable_declarator(ident),
                        rhs_at_use,
                    )
                    merged_decl = node_factory.create_local_variable_declaration(
                        type_node,
                        node_factory.create_declarator_list([init_decl]),
                    )
                    replace_stmt_at[fidx] = merged_decl
                    to_remove_from_decl.setdefault(decl_idx, set()).add(name)
                else:
                    # Pure move: randomly place the declaration-only statement somewhere before first use, excluding the original slot
                    ident = get_identifier_from_declarator(declarator)
                    new_decl = node_factory.create_local_variable_declaration(
                        type_node,
                        node_factory.create_declarator_list(
                            [node_factory.create_variable_declarator(ident)]
                        ),
                    )
                    slot = choose_slot(fidx, original_slot)  # Up to and including first use, excluding the original slot
                    inserts_at_slot[slot].append(new_decl)
                    # Remove v from the original declaration
                    to_remove_from_decl.setdefault(decl_idx, set()).add(name)

        # === Phase 4: rebuild the statement sequence
        new_list: List[Statement] = []
        for i in range(N):
            # 4.1 Insert before statement i
            if inserts_at_slot[i]:
                new_list.extend(inserts_at_slot[i])

            stmt = original[i]

            # 4.2 If this is an original declaration statement, remove selected variables from it
            if isinstance(stmt, LocalVariableDeclaration):
                to_remove = to_remove_from_decl.get(i, set())
                if to_remove:
                    # Rebuild the declarator list without removed variables
                    kept_decls: List[Declarator] = []
                    for d in stmt.declarators.node_list:
                        vname = get_identifier_from_declarator(d).name
                        if vname in to_remove:
                            continue
                        kept_decls.append(d)
                    if kept_decls:
                        stmt = node_factory.create_local_variable_declaration(
                            stmt.type,
                            node_factory.create_declarator_list(kept_decls),
                        )
                    else:
                        stmt = None  # The declaration statement is now empty, so remove it entirely

            # 4.3 Replacement at first use (merge)
            if stmt is not None and (i in replace_stmt_at):
                # Replace the original statement with the merged initializing declaration
                stmt = replace_stmt_at[i]

            # 4.4 Emit the current statement if it still exists
            if stmt is not None:
                new_list.append(stmt)

            # 4.5 Insert after this statement (used for split init assignment statements)
            if i in inserts_after_stmt:
                new_list.extend(inserts_after_stmt[i])

        # 4.6 Insert at the end of the block
        if inserts_at_slot[N]:
            new_list.extend(inserts_at_slot[N])

        node.node_list = new_list

        # Keep behavior consistent with existing visitors: recurse only after rebuilding
        self.generic_visit(node, parent, parent_attr)
        return False, []
