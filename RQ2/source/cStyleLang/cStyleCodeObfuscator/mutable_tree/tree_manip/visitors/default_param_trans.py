#!/usr/bin/env python3
"""Conservative explicit-default-parameter rewrites.

Implemented rule (language-aware):
  receiver.indexOf(x) <-> receiver.indexOf(x, 0)

To avoid changing user-defined methods with the same name, the rule is enabled only
when the receiver can be conservatively recognized as a built-in string/array value:
  * Java: string literals or identifiers statically declared as String.
  * JavaScript: string/array literals. (Untyped identifiers are intentionally skipped.)
  * C++: not applicable.
"""
from __future__ import annotations
from typing import Optional, Dict

from .visitor import TransformingVisitor
from .repos_varDecl import get_identifier_from_declarator
from ...nodes import (
    Node, Literal, ArrayExpression, Identifier, FieldAccess, CallExpression,
    LocalVariableDeclaration, TypedFormalParameter, node_factory,
)


def _type_name(decl_type) -> str:
    try:
        tid = decl_type.type_id
        if hasattr(tid, "type_identifier"):
            return str(tid.type_identifier)
        # QualifiedIdentifier fallback; only the terminal name matters here.
        name = getattr(tid, "name", None)
        if hasattr(name, "type_identifier"):
            return str(name.type_identifier)
        if hasattr(name, "name"):
            return str(name.name)
    except Exception:
        pass
    return ""


def _is_zero(expr: Node) -> bool:
    return isinstance(expr, Literal) and str(expr.value) in {"0", "0L", "0l"}


def _is_string_literal(expr: Node) -> bool:
    return isinstance(expr, Literal) and isinstance(expr.value, str) and (
        (expr.value.startswith('"') and expr.value.endswith('"'))
        or (expr.value.startswith("'") and expr.value.endswith("'"))
    )


class DefaultParamTransVisitor(TransformingVisitor):
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

    def _receiver_is_safe(self, recv: Node) -> bool:
        if self.lang == "cpp":
            return False
        if _is_string_literal(recv):
            return True
        if self.lang == "javascript" and isinstance(recv, ArrayExpression):
            return True
        if self.lang == "java" and isinstance(recv, Identifier):
            t = self._declared_types.get(recv.name, "")
            # Strip simple generic/qualified decorations conservatively.
            return t.split(".")[-1] == "String"
        return False

    def visit_CallExpression(self, node: CallExpression,
                             parent: Optional[Node] = None,
                             parent_attr: Optional[str] = None):
        self.generic_visit(node, parent, parent_attr)
        callee = node.callee
        if not isinstance(callee, FieldAccess):
            return False, []
        field = callee.field
        if not isinstance(field, Identifier) or field.name != "indexOf":
            return False, []
        if not self._receiver_is_safe(callee.object):
            return False, []

        args = list(node.args.get_children())
        if len(args) == 1:
            node.args = node_factory.create_expression_list(args + [node_factory.create_literal("0")])
            return True, [node]
        if len(args) == 2 and _is_zero(args[1]):
            node.args = node_factory.create_expression_list([args[0]])
            return True, [node]
        return False, []
