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
    # 复用你给过的取标识符逻辑
    if isinstance(node, VariableDeclarator):
        return node.decl_id
    else:
        return get_identifier_from_declarator(node.declarator)


def get_all_identifiers(node: Node) -> List[str]:
    # 复用 var_pos 风格的标识符收集（不做改动以最大复用）
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
    若 stmt 是 'var_name = <rhs>;' 这种简单赋值，返回 rhs；否则返回 None。
    """
    if isinstance(stmt, ExpressionStatement) and isinstance(stmt.expr, AssignmentExpression):
        assign = stmt.expr
        if assign.op == AssignmentOps.EQUAL and isinstance(assign.left, Identifier):
            if assign.left.name == var_name:
                return assign.right
    return None


class ReposVarDeclVisitor(TransformingVisitor):
    """
    对 StatementList：
      1) 找到所有变量 v 的声明位置与首次使用位置；
      2) 分情况对 v 的声明进行：
         - 若“声明即初始化”（声明位置 == 首次使用位置）：
             (a) 若该处仍有其它相同类型的声明（同一条 LocalVariableDeclaration 里还有别的声明符）：
                 将 v 的“声明/初始化”拆开：在原位置“下一条语句处”放入 'v = init;'（赋值语句）；
                 同时把“声明”（不带初始化）随机放到 [块首..初始化位置之前] 的任意槽位（可含 slot=decl_idx）；
             (b) 若该处没有其它相同类型声明（独占一条）：
                 删除该条“带初始化声明”，在其“下一条语句处”放入 'v = init;'；
                 并把“声明”（不带初始化）随机放到 [块首..初始化位置之前] 的任意槽位。
         - 若“声明与首次使用不同位置”：
             (a) 若该处仍有其它相同类型声明：可二选一（随机）：
                 - 移动“声明”（不带初始化）到 [块首..首次使用之前] 的任意槽位（不包含初始槽位）；
                 - 或与“首次使用”合并（若首次使用是 'v = rhs;'），在首次使用处生成 'T v = rhs;' 替换该赋值。
             (b) 若该处没有其它相同类型声明：同上二选一（移动或合并）。
      注：若候选槽位在排除原槽位后为空，则退回原槽位（务实回退）。
    """

    def __init__(self, seed: Optional[int] = None, prefer_merge_prob: float = 0.5):
        super().__init__()
        self._rng = random.Random(seed)
        self._prefer_merge_prob = prefer_merge_prob  # 控制 3.* 情况下“移动 vs 合并”的概率

    def visit_StatementList(
        self,
        node: StatementList,
        parent: Optional[Node] = None,
        parent_attr: Optional[str] = None,
    ):
        # === Phase 0: 拿到原始语句序列（不立即修改）
        original: List[Statement] = []
        for attr in node.get_children_names():
            ch = node.get_child_at(attr)
            if ch is None:
                continue
            original.append(cast(Statement, ch))
        N = len(original)

        # === Phase 1: 收集所有变量的声明信息
        # name -> (decl_idx, decl_stmt: LocalVariableDeclaration, declarator, has_init, init_value_if_any, type_node, multi_in_stmt)
        VarInfo = Tuple[int, LocalVariableDeclaration, Declarator, bool, Optional[Node], Node, bool]
        var_info: Dict[str, VarInfo] = {}
        # 记录每条 LocalVariableDeclaration 的所有变量名（便于判断“是否还有其他相同类型声明”）
        decl_stmt_vars: Dict[int, List[str]] = {}

        for idx, stmt in enumerate(original):
            if not isinstance(stmt, LocalVariableDeclaration):
                continue

            all_decls = stmt.declarators.node_list  # 该条声明语句中的所有声明符
            names_in_stmt: List[str] = []
            for d in all_decls:
                # tree-sitter 有时把 initializer 识别为 FunctionDeclarator，这里与原脚本一致地视为“带初始化”
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

        # === Phase 2: 计算首次使用位置
        first_use_idx: Dict[str, int] = {}
        for name, (decl_idx, _decl_stmt, _declarator, has_init, _init_val, _type_node, _multi) in var_info.items():
            if has_init:
                # 声明即初始化：首次使用=声明位置
                first_use_idx[name] = decl_idx
            else:
                # 从声明之后开始找第一次出现
                found = None
                for j in range(decl_idx + 1, N):
                    if name in get_all_identifiers(original[j]):
                        found = j
                        break
                if found is not None:
                    first_use_idx[name] = found
                else:
                    # 若未发现使用，就视为“未使用”，我们把 first_use 定义为块尾（用于随机槽位上界）
                    first_use_idx[name] = N

        # === Phase 3: 计划修改（不立刻改 AST）
        # 3.1 需要从原声明语句删除的变量
        to_remove_from_decl: Dict[int, Set[str]] = {}
        # 3.2 在某个“slot”（插入点）前插入的新“仅声明”语句（不带初始化）
        inserts_at_slot: Dict[int, List[Statement]] = {i: [] for i in range(N + 1)}
        # 3.3 在某条语句之后插入的新语句（用于“init 拆成赋值语句放在下一条”）
        inserts_after_stmt: Dict[int, List[Statement]] = {}
        # 3.4 替换某条语句（用于“合并：用初始化式声明替换首次使用处的赋值语句”）
        replace_stmt_at: Dict[int, Statement] = {}

        def choose_slot(upto_inclusive: int, exclude_slot: int) -> int:
            """
            从槽位 {0..upto_inclusive} 中随机选择一个，排除 exclude_slot。
            若空集则回退到 exclude_slot。
            """
            if upto_inclusive < 0:
                return exclude_slot
            candidates = list(range(0, min(upto_inclusive, N) + 1))
            if exclude_slot in candidates:
                candidates.remove(exclude_slot)
            if not candidates:
                return exclude_slot
            return self._rng.choice(candidates)

        # 3.5：为每个变量规划动作
        for name, (decl_idx, decl_stmt, declarator, has_init, init_val, type_node, multi_in_stmt) in var_info.items():
            fidx = first_use_idx[name]  # 首次使用（或 N=块尾）
            original_slot = decl_idx     # 原声明插入槽位（即“在该语句之前”）

            # case A: 声明即初始化（decl == first use）
            if has_init and fidx == decl_idx:
                # 拆分为“声明 + 赋值”，赋值放在“原位置的下一条语句”处
                # 赋值语句
                ident = get_identifier_from_declarator(declarator)
                if isinstance(declarator, InitializingDeclarator):
                    rhs = init_val
                else:
                    # FunctionDeclarator 特例等，无显式 value；此时不做拆分以免构造不完整 rhs
                    # 直接跳过（也可改为仅移动声明，视需要）
                    continue

                assign_expr = node_factory.create_assignment_expr(ident, rhs, AssignmentOps.EQUAL)
                assign_stmt = node_factory.create_expression_stmt(assign_expr)
                inserts_after_stmt.setdefault(decl_idx, []).append(assign_stmt)

                # 从原声明里移除 v
                to_remove_from_decl.setdefault(decl_idx, set()).add(name)

                # “声明（不带 init）”随机放到 [块首..初始化位置之前] 的槽位
                # 初始化位置在 decl_idx+1 的前一条，即 upto = decl_idx
                # 若该处还有其它同类型声明（multi_in_stmt=True），或独占一条，都这么做
                new_decl = node_factory.create_local_variable_declaration(
                    type_node,
                    node_factory.create_declarator_list(
                        [node_factory.create_variable_declarator(ident)]
                    ),
                )
                slot = choose_slot(decl_idx, original_slot)  # 允许 decl_idx, 排除原槽位
                inserts_at_slot[slot].append(new_decl)

            # case B: 声明与首次使用不同位置
            else:
                # 二选一：合并 或 移动（若首次使用不是简单赋值，则只能“移动”）
                do_merge = self._rng.random() < self._prefer_merge_prob
                rhs_at_use = None
                if fidx < N:
                    rhs_at_use = _match_simple_assign_to_var(original[fidx], name)

                if do_merge and (rhs_at_use is not None):
                    # 合并：在首次使用处用“初始化式声明”替换原赋值；并从原声明处删除 v
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
                    # 纯移动：把“仅声明”随机放到 [块首..首次使用之前] 的任意槽位（不含原槽位）
                    ident = get_identifier_from_declarator(declarator)
                    new_decl = node_factory.create_local_variable_declaration(
                        type_node,
                        node_factory.create_declarator_list(
                            [node_factory.create_variable_declarator(ident)]
                        ),
                    )
                    slot = choose_slot(fidx, original_slot)  # 到 first-use 之前（含），排除原槽位
                    inserts_at_slot[slot].append(new_decl)
                    # 从原声明处删除 v
                    to_remove_from_decl.setdefault(decl_idx, set()).add(name)

        # === Phase 4: 重建语句序列
        new_list: List[Statement] = []
        for i in range(N):
            # 4.1 在第 i 条语句之前插入
            if inserts_at_slot[i]:
                new_list.extend(inserts_at_slot[i])

            stmt = original[i]

            # 4.2 如果这是原声明语句，需要删除其中的若干变量
            if isinstance(stmt, LocalVariableDeclaration):
                to_remove = to_remove_from_decl.get(i, set())
                if to_remove:
                    # 重建 declarator_list，去掉被删除的变量
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
                        stmt = None  # 该声明语句已空，整体删除

            # 4.3 首次使用处的替换（合并）
            if stmt is not None and (i in replace_stmt_at):
                # 用合并后的初始化式声明替换原语句
                stmt = replace_stmt_at[i]

            # 4.4 输出本条（若仍存在）
            if stmt is not None:
                new_list.append(stmt)

            # 4.5 在该条语句之后的插入（用于“init 拆分”的赋值语句）
            if i in inserts_after_stmt:
                new_list.extend(inserts_after_stmt[i])

        # 4.6 块尾插入
        if inserts_at_slot[N]:
            new_list.extend(inserts_at_slot[N])

        node.node_list = new_list

        # 与既有 visitor 一致：重建后再递归访问子树
        self.generic_visit(node, parent, parent_attr)
        return False, []
