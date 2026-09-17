from cStyleCodeObfuscator.mutable_tree.nodes import node_factory
from cStyleCodeObfuscator.mutable_tree.nodes import BinaryOps, AssignmentOps, UpdateOps
from cStyleCodeObfuscator.mutable_tree.tree_manip.visitors.default_param_trans import DefaultParamTransVisitor
from cStyleCodeObfuscator.mutable_tree.tree_manip.visitors.equivalent_forms_trans import EquivalentFormsTransVisitor
from cStyleCodeObfuscator.mutable_tree.tree_manip.visitors.update_trans import UpdateTransVisitor


def test_default_param_string_literal_java_roundtrip_forward():
    recv = node_factory.create_literal('"abc"')
    callee = node_factory.create_field_access(recv, node_factory.create_identifier("indexOf"))
    call = node_factory.create_call_expr(callee, node_factory.create_expression_list([node_factory.create_literal('"b"')]))
    DefaultParamTransVisitor("java").visit(call)
    args = call.args.get_children()
    assert len(args) == 2
    assert str(args[1].value) == "0"


def test_null_comparison_swap_java():
    expr = node_factory.create_binary_expr(
        node_factory.create_identifier("x"), node_factory.create_literal("null"), BinaryOps.NE
    )
    EquivalentFormsTransVisitor("java").visit(expr)
    assert getattr(expr.left, "value", None) == "null"
    assert getattr(expr.right, "name", None) == "x"


def test_java_collection_isempty_to_size_zero_with_type_evidence():
    decl_type = node_factory.create_declarator_type(node_factory.create_type_identifier("List"))
    decl = node_factory.create_local_variable_declaration(
        decl_type,
        node_factory.create_declarator_list([
            node_factory.create_variable_declarator(node_factory.create_identifier("xs"))
        ]),
    )
    callee = node_factory.create_field_access(node_factory.create_identifier("xs"), node_factory.create_identifier("isEmpty"))
    call = node_factory.create_call_expr(callee, node_factory.create_expression_list([]))
    stmt = node_factory.create_expression_stmt(call)
    block = node_factory.create_statement_list([decl, stmt])
    EquivalentFormsTransVisitor("java").visit(block)
    transformed = block.node_list[1].expr
    assert transformed.op == BinaryOps.EQ
    assert getattr(transformed.right, "value", None) == "0"
    assert getattr(transformed.left.callee.field, "name", None) == "size"


def test_update_safe_mode_rewrites_standalone_but_not_value_consuming():
    # Standalone i++ may be represented differently because its value is ignored.
    up = node_factory.create_update_expr(node_factory.create_identifier("i"), UpdateOps.INCREMENT, False)
    stmt = node_factory.create_expression_stmt(up)
    UpdateTransVisitor(seed=7, safe_only=True).visit(stmt)
    assert stmt.expr is not up

    # x = i++ must not be rewritten to ++i / i += 1 because the postfix value is consumed.
    nested_up = node_factory.create_update_expr(node_factory.create_identifier("i"), UpdateOps.INCREMENT, False)
    assn = node_factory.create_assignment_expr(node_factory.create_identifier("x"), nested_up, AssignmentOps.EQUAL)
    stmt2 = node_factory.create_expression_stmt(assn)
    UpdateTransVisitor(seed=7, safe_only=True).visit(stmt2)
    assert stmt2.expr.right is nested_up
