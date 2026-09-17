#!/usr/bin/env python3
"""Conservative semantics-preserving expression rewrites.

Rules:
  1. Null-comparison operand swap:
       x != null <-> null != x, x == null <-> null == x
     (Java/JavaScript; C++ additionally recognizes nullptr/NULL).
  2. Empty/size equivalence for statically recognized standard containers:
       obj.isEmpty() <-> obj.size() == 0      (Java)
       obj.empty()   <-> obj.size() == 0      (C++)

The container rule is intentionally guarded by simple local type evidence. Unknown
receivers are skipped rather than guessed.
"""
from __future__ import annotations
from typing import Optional, Dict, Set

from .visitor import TransformingVisitor
from .repos_varDecl import get_identifier_from_declarator
from .default_param_trans import _type_name
from ...nodes import (
    Node, Literal, Identifier, FieldAccess, CallExpression, BinaryExpression,
    LocalVariableDeclaration, TypedFormalParameter, BinaryOps, node_factory,
)

JAVA_CONTAINER_TYPES: Set[str] = {
    "Collection", "List", "ArrayList", "LinkedList", "Set", "HashSet", "TreeSet",
    "Map", "HashMap", "TreeMap", "Queue", "Deque", "ArrayDeque", "Vector", "Stack",
}
CPP_CONTAINER_TYPES: Set[str] = {
    "vector", "list", "deque", "set", "multiset", "map", "multimap",
    "unordered_set", "unordered_map", "string", "array", "forward_list",
}


def _terminal_type_name(name: str) -> str:
    name = name.replace("std::", "")
    if "<" in name:
        name = name.split("<", 1)[0]
    if "." in name:
        name = name.rsplit(".", 1)[-1]
    return name.strip()


def _is_null_literal(expr: Node, lang: str) -> bool:
    if not isinstance(expr, Literal):
        return False
    v = str(expr.value)
    if lang in {"java", "javascript"}:
        return v == "null"
    return v in {"nullptr", "NULL"}


def _zero(expr: Node) -> bool:
    return isinstance(expr, Literal) and str(expr.value) in {"0", "0L", "0l", "0U", "0u"}


def _field_call(receiver: Node, name: str) -> CallExpression:
    callee = node_factory.create_field_access(receiver, node_factory.create_identifier(name))
    return node_factory.create_call_expr(callee, node_factory.create_expression_list([]))


class EquivalentFormsTransVisitor(TransformingVisitor):
    def __init__(self, lang: str):
        super().__init__()
        self.lang = lang
        self._declared_types: Dict[str, str] = {}

    def visit_LocalVariableDeclaration(self, node: LocalVariableDeclaration,
                                       parent: Optional[Node] = None,
                                       parent_attr: Optional[str] = None):
        tname = _type_name(node.type)
        for d in node.declarators.get_children():
            try:
                ident = get_identifier_from_declarator(d)
                self._declared_types[ident.name] = tname
            except Exception:
                pass
        return self.generic_visit(node, parent, parent_attr)

    def visit_TypedFormalParameter(self, node: TypedFormalParameter,
                                   parent: Optional[Node] = None,
                                   parent_attr: Optional[str] = None):
        if node.declarator is not None:
            try:
                ident = get_identifier_from_declarator(node.declarator)
                self._declared_types[ident.name] = _type_name(node.decl_type)
            except Exception:
                pass
        return self.generic_visit(node, parent, parent_attr)

    def _known_container(self, recv: Node) -> bool:
        if not isinstance(recv, Identifier):
            return False
        t = _terminal_type_name(self._declared_types.get(recv.name, ""))
        if self.lang == "java":
            return t in JAVA_CONTAINER_TYPES
        if self.lang == "cpp":
            return t in CPP_CONTAINER_TYPES
        return False

    def visit_BinaryExpression(self, node: BinaryExpression,
                               parent: Optional[Node] = None,
                               parent_attr: Optional[str] = None):
        self.generic_visit(node, parent, parent_attr)

        # Rule 1: equality/inequality operand swap around null.
        if node.op in {BinaryOps.EQ, BinaryOps.NE, BinaryOps.EQQ, BinaryOps.NEQQ}:
            left_null = _is_null_literal(node.left, self.lang)
            right_null = _is_null_literal(node.right, self.lang)
            if left_null ^ right_null:
                node.left, node.right = node.right, node.left
                return True, [node]

        # Rule 2 reverse: size()==0 -> isEmpty()/empty(), with static receiver evidence.
        if node.op in {BinaryOps.EQ, BinaryOps.EQQ}:
            call, z = None, None
            if isinstance(node.left, CallExpression) and _zero(node.right):
                call, z = node.left, node.right
            elif isinstance(node.right, CallExpression) and _zero(node.left):
                call, z = node.right, node.left
            if call is not None and isinstance(call.callee, FieldAccess):
                fld = call.callee.field
                if isinstance(fld, Identifier) and fld.name == "size" and len(call.args.get_children()) == 0:
                    recv = call.callee.object
                    if self._known_container(recv):
                        m = "isEmpty" if self.lang == "java" else "empty"
                        return True, [_field_call(recv, m)]
        return False, []

    def visit_CallExpression(self, node: CallExpression,
                             parent: Optional[Node] = None,
                             parent_attr: Optional[str] = None):
        self.generic_visit(node, parent, parent_attr)
        if not isinstance(node.callee, FieldAccess) or len(node.args.get_children()) != 0:
            return False, []
        fld = node.callee.field
        if not isinstance(fld, Identifier):
            return False, []
        recv = node.callee.object
        if not self._known_container(recv):
            return False, []
        expected = "isEmpty" if self.lang == "java" else "empty"
        if fld.name != expected:
            return False, []
        size_call = _field_call(recv, "size")
        expr = node_factory.create_binary_expr(size_call, node_factory.create_literal("0"), BinaryOps.EQ)
        return True, [expr]
