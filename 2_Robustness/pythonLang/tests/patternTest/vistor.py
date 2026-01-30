import libcst as cst
from pyCodeObfuscator.core.parser import parse_code
#TODO: NL
from pyCodeObfuscator.patterns.NL.naming_style_pattern import (
    match_naming_style,
    NamingStyleMatch,
)
#TODO: AL.expression
from pyCodeObfuscator.patterns.AL.expression.boolean_explicit_true_false_pattern import (
    match_boolean_explicit_true_false,
    BooleanExplicitTrueFalseMatch,
)
from pyCodeObfuscator.patterns.AL.expression.condition_parentheses_pattern import (
    match_condition_parentheses,
    ConditionParenthesesMatch,
)
from pyCodeObfuscator.patterns.AL.expression.dict_keys_usage_pattern import (
    match_dict_keys_usage,
    DictKeysUsageMatch,
)
from pyCodeObfuscator.patterns.AL.expression.format_percent_usage_pattern import (
    match_format_percent_usage,
    FormatPercentUsageMatch,
)
from pyCodeObfuscator.patterns.AL.expression.none_usage_pattern import (
    match_none_usage,
    NoneUsageMatch,
)
from pyCodeObfuscator.patterns.AL.expression.op_opequal_usage_pattern import (
    OpOrOpEqualUsageMatch,
    match_op_opequal_usage,
)
from pyCodeObfuscator.patterns.AL.expression.parameter_default_sorted_pattern import (
    ParameterDefaultSortedMatch,
    match_parameter_default_sorted,
)
#TODO: AL.block
from pyCodeObfuscator.patterns.AL.block.for_to_list_comprehension_pattern import (
    match_for_list_comprehension_pair,
    ForListCompMatch,
)
from pyCodeObfuscator.patterns.AL.block.initialize_ways_pattern import (
    InitializeWaysMatch,
    match_initialize_ways_single,
    match_initialize_ways_pair,
)
from pyCodeObfuscator.patterns.AL.block.loop_index_direct_reference_pattern import (
    match_loop_index_direct_reference,
    LoopIndexDirectReferenceMatch,
)
from pyCodeObfuscator.patterns.AL.block.unnecessary_else_pattern import (
    match_remove_unnecessary_else,
    RemoveElseMatch,
)

class SPTPatternCollector(cst.CSTVisitor):
    def __init__(self) -> None:
        #TODO: NL
        self.naming_style_matches: list[NamingStyleMatch] = []
        #TODO: AL.expression
        self.bool_explicit_matches: list[BooleanExplicitTrueFalseMatch] = []
        self.condition_parens_matches: list[ConditionParenthesesMatch] = []
        self.dict_keys_matches: list[DictKeysUsageMatch] = []
        self.format_percent_matches: list[FormatPercentUsageMatch] = []
        self.none_usage_matches: list[NoneUsageMatch] = []
        self.op_opequal_usage_matches: list[OpOrOpEqualUsageMatch] = []
        self.parameter_default_sorted_matches: list[ParameterDefaultSortedMatch] = []
        #TODO: AL.block
        self.for_listcomp_matches: list[ForListCompMatch] = []
        self.initialize_ways_matches: list[InitializeWaysMatch] = []
        self.loop_index_matches: list[LoopIndexDirectReferenceMatch] = []
        self.remove_else_matches: list[RemoveElseMatch] = []
        self._last_simple_stmt: cst.SimpleStatementLine | None = None

    #TODO: NL
    def visit_Name(self, node: cst.Name) -> None:
        m1 = match_naming_style(node)
        if m1 is not None:
            self.naming_style_matches.append(m1)
    
    #TODO: AL
    def visit_BinaryOperation(self, node: cst.BinaryOperation) -> None:
        m1 = match_format_percent_usage(node)
        if m1 is not None:
            self.format_percent_matches.append(m1)

    def visit_SimpleStatementLine(self, node: cst.SimpleStatementLine) -> None:
        m1 = match_op_opequal_usage(node)
        if m1 is not None:
            self.op_opequal_usage_matches.append(m1)

        # 先尝试两行模式：上一个 simple stmt + 当前这个
        if self._last_simple_stmt is not None:
            pair = match_initialize_ways_pair(self._last_simple_stmt, node)
            if pair is not None:
                self.initialize_ways_matches.append(pair)

        # 当前这一行自身如果是 dict_call，也记录一下
        single = match_initialize_ways_single(node)
        if single is not None:
            self.initialize_ways_matches.append(single)

        self._last_simple_stmt = node
            
    def visit_Call(self, node: cst.Call) -> None:
        m1 = match_format_percent_usage(node)
        if m1 is not None:
            self.format_percent_matches.append(m1)
            
        m2 = match_parameter_default_sorted(node)
        if m2 is not None:
            self.parameter_default_sorted_matches.append(m2)
    
    # ---- 针对 If 节点的规则 ----
    def visit_If(self, node: cst.If) -> None:
        m1 = match_remove_unnecessary_else(node)
        if m1 is not None:
            self.remove_else_matches.append(m1)
            
        m2 = match_condition_parentheses(node.test)
        if m2 is not None:
            self.condition_parens_matches.append(m2)
            
        m3 = match_none_usage(node.test)
        if m3 is not None:
            self.none_usage_matches.append(m3)
    
    # ---- 针对 IfExp（三元表达式）节点的规则 ----        
    def visit_IfExp(self, node: cst.IfExp) -> None:
        m1 = match_condition_parentheses(node.test)
        if m1 is not None:
            self.condition_parens_matches.append(m1)
        
        m2 = match_none_usage(node.test)
        if m2 is not None:
            self.none_usage_matches.append(m2)
            
    # ---- 针对 CompIf（带 elif / else 的 if 语句）节点的规则 ----
    def visit_CompIf(self, node: cst.CompIf) -> None:
        m1 = match_condition_parentheses(node.test)
        if m1 is not None:
            self.condition_parens_matches.append(m1)
        
        m2 = match_none_usage(node.test)
        if m2 is not None:
            self.none_usage_matches.append(m2)

    # ---- 针对 For 节点的规则 ----
    def visit_For(self, node: cst.For) -> None:
        m1 = match_loop_index_direct_reference(node)
        if m1 is not None:
            self.loop_index_matches.append(m1)
    
    # ---- 针对 While 节点的规则 ----
    def visit_While(self, node: cst.While) -> None:
        m1 = match_condition_parentheses(node.test)
        if m1 is not None:
            self.condition_parens_matches.append(m1)
            
        m2 = match_none_usage(node.test)
        if m2 is not None:
            self.none_usage_matches.append(m2)
    
    # ---- 针对 Comparison 节点的规则 ----
    def visit_Comparison(self, node: cst.Comparison) -> None:
        m = match_dict_keys_usage(node)
        if m is not None:
            self.dict_keys_matches.append(m)

    # ---- 针对 Assign（表达式级规则看 RHS）----
    def visit_Assign(self, node: cst.Assign) -> None:
        m1 = match_boolean_explicit_true_false(node.value)
        if m1 is not None:
            self.bool_explicit_matches.append(m1)
            
    # ---- 针对 Assert 节点的规则 ----
    def visit_Assert(self, node: cst.Assert) -> None:
        m1 = match_condition_parentheses(node.test)
        if m1 is not None:
            self.condition_parens_matches.append(m1) 
            
        m2 = match_none_usage(node.test)
        if m2 is not None:
            self.none_usage_matches.append(m2)
            
    # ---- 针对块级语句序列的规则（for 循环 <-> 列表推导）----
    def visit_IndentedBlock(self, node: cst.IndentedBlock) -> None:
        self._collect_for_listcomp_in_body(node.body)

    def visit_Module(self, node: cst.Module) -> None:
        # 顶层语句序列同样跑一次 for -> list comprehension 的模式匹配
        self._collect_for_listcomp_in_body(node.body)

    def _collect_for_listcomp_in_body(
        self, body: list[cst.BaseStatement]
    ) -> None:
        stmts = list(body)
        n = len(stmts)
        i = 0
        while i < n:
            stmt = stmts[i]
            next_stmt = stmts[i + 1] if i + 1 < n else None
            m = match_for_list_comprehension_pair(stmt, next_stmt)
            if m is not None:
                self.for_listcomp_matches.append(m)
            i += 1


def collect_all_patterns(source: str) -> tuple[SPTPatternCollector, cst.Module]:
    module = parse_code(source)
    collector = SPTPatternCollector()
    module.visit(collector)
    return collector, module
