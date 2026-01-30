#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
idRename.py

A combination visitor that rename identifier(replace&append) in C-style language ASTs.
- identifier_rename.py

Author: Cruise-z <cruise.zrz@gmail.com>
Affiliation: IIE CAS
Date: 2025-11-08
"""
import random
import string
from typing import Optional

from .visitor import TransformingVisitor
from .var_name_utils import sanitize_name_for_styling

from ...nodes import Node, NodeType, node_factory
from ...nodes import VariableDeclarator, Identifier, FunctionDeclarator


# class IdRenameVisitor(TransformingVisitor):
#     """
#     Randomly *rename* or *append-suffix* to identifiers, while keeping usages consistent.

#     Behavior
#     --------
#     - When visiting a VariableDeclarator (i.e., a variable definition), we decide *once*
#       for that variable name to either:
#         * REPLACE:   name -> <random_token>
#         * APPEND:    name -> name + ucfirst(<random_token>)
#       The choice is random (50/50 by default) but can be controlled via `p_append`.
#     - All subsequent Identifier occurrences of that variable are rewritten accordingly.
#     - We avoid touching:
#         * member-access fields:  obj.<field>
#         * call callees:          <callee>(...)
#         * function names (we only recurse into parameters of a FunctionDeclarator that
#           sits under a FUNCTION_HEADER)

#     Notes
#     -----
#     - Generated tokens are valid identifiers: first char is [A-Za-z_], rest are [A-Za-z0-9_].
#     - We run generated names through `sanitize_name_for_styling` to avoid keywords etc.
#     - This visitor is *declaration-driven*: we create the mapping at declarations
#       (VariableDeclarator), then apply it everywhere via Identifier visits.
#     """

#     def __init__(self, seed: Optional[int] = None, p_append: float = 0.5,
#                  min_len: int = 3, max_len: int = 8):
#         super().__init__()
#         self._rng = random.Random(seed)
#         self.p_append = p_append
#         self.min_len = max(1, int(min_len))
#         self.max_len = max(self.min_len, int(max_len))
#         # original_name -> new_name
#         self._name_map = {}

#     # ---------- utils ----------

#     def _rand_ident_token(self) -> str:
#         """Generate a random identifier token that doesn't start with a digit."""
#         first = self._rng.choice(string.ascii_letters + "_")
#         n = self._rng.randint(self.min_len - 1, self.max_len - 1)
#         rest = "".join(self._rng.choices(string.ascii_letters + string.digits + "_", k=n))
#         raw = first + rest
#         return sanitize_name_for_styling(raw)

#     def _append_style(self, base: str, suffix: str) -> str:
#         """Append suffix with capitalized first letter (e.g., 'count' + 'tmp' -> 'countTmp')."""
#         if not suffix:
#             return base
#         if len(suffix) == 1:
#             out = base + suffix[0].upper()
#         else:
#             out = base + suffix[0].upper() + suffix[1:]
#         return sanitize_name_for_styling(out)

#     # ---------- structure traversal rules ----------

#     def visit_FunctionDeclarator(
#         self,
#         node: FunctionDeclarator,
#         parent: Optional[Node] = None,
#         parent_attr: Optional[str] = None,
#     ):
#         # Do not rename the function name itself. Only dive into its parameters when
#         # it's under a FUNCTION_HEADER (parity with your existing visitors).
#         if parent is not None and parent.node_type == NodeType.FUNCTION_HEADER:
#             self.generic_visit(node.parameters, node, "parameters")
#             return False, []
#         return self.generic_visit(node, parent, parent_attr)

#     def visit_VariableDeclarator(
#         self,
#         node: VariableDeclarator,
#         parent: Optional[Node] = None,
#         parent_attr: Optional[str] = None,
#     ):
#         old = node.decl_id.name

#         if old not in self._name_map:
#             # decide strategy for this variable
#             do_append = (self._rng.random() < self.p_append)
#             token = self._rand_ident_token()

#             if do_append:
#                 new_name = self._append_style(old, token)
#             else:
#                 new_name = token

#             # avoid accidental no-op
#             if new_name == old:
#                 # regenerate once
#                 token = self._rand_ident_token()
#                 new_name = self._append_style(old, token) if do_append else token

#             self._name_map[old] = new_name

#         # rewrite declarator id
#         new_id = node_factory.create_identifier(self._name_map[old])
#         return True, [node_factory.create_variable_declarator(new_id)]

#     def visit_Identifier(
#         self,
#         node: Identifier,
#         parent: Optional[Node] = None,
#         parent_attr: Optional[str] = None,
#     ):
#         # Skip unsafe/undesired positions
#         if parent is not None:
#             if parent.node_type == NodeType.FIELD_ACCESS and parent_attr == "field":
#                 return False, []
#             if parent.node_type == NodeType.CALL_EXPR and parent_attr == "callee":
#                 return False, []

#         name = node.name
#         new_name = self._name_map.get(name)
#         if new_name is None:
#             return False, []

#         return True, [node_factory.create_identifier(new_name)]

class IdRenameVisitor(TransformingVisitor):
    """
    REPLACE-ONLY (style-preserving):
      - Each declared variable is replaced by a randomly generated identifier
        that **keeps the original naming style**:
          * underscores remain at the same positions,
          * each non-underscore segment is replaced with an equal-length token,
          * per-character case is preserved (A→A, a→a),
          * digits remain digits (only values change, not positions).
      - All subsequent Identifier occurrences are rewritten consistently.

    Interface kept compatible with previous version (p_append retained but ignored).

    Safety:
      - Skips member-access fields (obj.<field>) and call callees (<callee>(...)).
      - Does not rename function names; only descends into parameters when the
        FunctionDeclarator sits under a FUNCTION_HEADER.
      - Generated names contain only [A-Za-z0-9_] and start with [A-Za-z_]
        (same as original validity); we ensure sanitize_name_for_styling does not alter it
        (i.e., avoid accidentally generating keywords) by re-sampling if it changes.
    """

    def __init__(self, seed: Optional[int] = None, p_append: float = 0.5,
                 min_len: int = 3, max_len: int = 32):
        """
        Args:
            seed: RNG seed for reproducibility.
            p_append: kept for compatibility; ignored (no append mode).
            min_len, max_len: legacy knobs; NOT used for style-preserving mode,
                              but kept for API compatibility.
        """
        super().__init__()
        self._rng = random.Random(seed)
        # p_append kept for API compatibility but unused in REPLACE-only mode
        self.p_append = p_append
        # Not used for length anymore (we preserve original length), but keep for API compat
        self.min_len = max(1, int(min_len))
        self.max_len = max(self.min_len, int(max_len))
        # original_name -> new_name
        self._name_map = {}

    # ---------- utils (style-preserving generators) ----------

    def _rand_letter_like(self, upper: bool) -> str:
        """Random letter with requested case."""
        if upper:
            return self._rng.choice(string.ascii_uppercase)
        else:
            return self._rng.choice(string.ascii_lowercase)

    def _rand_digit(self) -> str:
        return self._rng.choice(string.digits)

    def _rand_like_name(self, old: str) -> str:
        """
        Generate a random identifier of the SAME SHAPE as `old`:
          - underscores stay as '_'
          - for each alphabetic char: random letter with the same case at that position
          - for each digit: random digit
        Ensures the first character is not a digit (same as valid identifiers).
        """
        if not old:
            # Fallback: minimal valid name
            return "x"

        out_chars = []
        for i, ch in enumerate(old):
            if ch == "_":
                out_chars.append("_")
            elif ch.isalpha():
                out_chars.append(self._rand_letter_like(ch.isupper()))
            elif ch.isdigit():
                # digits remain digits; first char of identifiers cannot be a digit
                if i == 0:
                    # old[0] should never be a digit in a valid identifier; just in case:
                    # choose a letter with lowercase by default (style-agnostic fallback)
                    out_chars.append(self._rand_letter_like(upper=False))
                else:
                    out_chars.append(self._rand_digit())
            else:
                # Any non-identifier char shouldn't appear in a valid name;
                # fall back to an underscore at the same position.
                out_chars.append("_")

        # Ensure first character is valid (letter or underscore). Given a valid source name,
        # this should already hold; keep an extra guard.
        if out_chars and out_chars[0].isdigit():
            # Choose a letter; mimic the source's first char category if possible
            # (underscore stays underscore; letter keeps case). If source starts
            # with underscore, leaving underscore is fine.
            out_chars[0] = self._rand_letter_like(upper=old[0].isupper() if old[0].isalpha() else False)

        return "".join(out_chars)

    def _rand_style_preserving_ident(self, old: str, max_attempts: int = 10) -> str:
        """
        Sample a new identifier that preserves style/shape and is not altered by
        sanitize_name_for_styling (avoid keywords). Retry a few times if needed.
        """
        for _ in range(max_attempts):
            candidate = self._rand_like_name(old)
            # Avoid accidental no-op
            if candidate == old:
                continue
            sanitized = sanitize_name_for_styling(candidate)
            # Only accept if sanitize doesn't modify the token (e.g., keyword handling)
            if sanitized == candidate:
                return candidate
        # As a last resort, return candidate even if sanitized changed it—still valid.
        return sanitized

    # ---------- structure traversal rules ----------

    def visit_FunctionDeclarator(
        self,
        node: FunctionDeclarator,
        parent: Optional[Node] = None,
        parent_attr: Optional[str] = None,
    ):
        # Do not rename the function name itself. Only dive into its parameters when
        # it's under a FUNCTION_HEADER (parity with your existing visitors).
        if parent is not None and parent.node_type == NodeType.FUNCTION_HEADER:
            self.generic_visit(node.parameters, node, "parameters")
            return False, []
        return self.generic_visit(node, parent, parent_attr)

    def visit_VariableDeclarator(
        self,
        node: VariableDeclarator,
        parent: Optional[Node] = None,
        parent_attr: Optional[str] = None,
    ):
        old = node.decl_id.name

        if old not in self._name_map:
            # REPLACE with style-preserving token
            new_name = self._rand_style_preserving_ident(old)

            # ensure actual change; retry already handled inside _rand_style_preserving_ident
            self._name_map[old] = new_name

        # rewrite declarator id
        new_id = node_factory.create_identifier(self._name_map[old])
        return True, [node_factory.create_variable_declarator(new_id)]

    def visit_Identifier(
        self,
        node: Identifier,
        parent: Optional[Node] = None,
        parent_attr: Optional[str] = None,
    ):
        # Skip unsafe/undesired positions
        if parent is not None:
            if parent.node_type == NodeType.FIELD_ACCESS and parent_attr == "field":
                return False, []
            if parent.node_type == NodeType.CALL_EXPR and parent_attr == "callee":
                return False, []

        name = node.name
        new_name = self._name_map.get(name)
        if new_name is None:
            return False, []

        return True, [node_factory.create_identifier(new_name)]
