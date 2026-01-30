from vistor import collect_all_patterns

source = """
def name_style_test():
    userAddNum = 1
    user_add_num = 2
    user_Add_Num = 3
    total = userAddNum + user_add_num + user_Add_Num
    return total

def f(a=None):
    if a is None:
        print("zzz")
        return 1
    else:
        x = 2
        print(x)
        ADD = []
        for i in range(3):
            ADD.append(i)
        for currency_idx in range(len(currencies)):
            print(currencies[currency_idx])
    z = z +1
    value_expr   = True if (a > 0 and b < 5) else False

def g(a=None):
    if a is None:
        print("zzz")
        return 1
    x += 2
    print(x)
    flag1 = a > 0
    
def parentheses_test(userid, xs):
    assert (userid == 0)
    assert userid is not None
    while (userid == 0):
        return 0
    return [x for x in xs if (x > 0)]
    return 0 if (userid == 0) else 1
    
def dict_keys_usage_test(d):
    if "Alice" in d:
        a = 1
    if "Bob" in d.keys():
        b = 2
    return a + b

def format_percent_usage_test(h, w):
    s1 = "Height: %d, Width: %d" % (h, w)
    s2 = "Size: {},{}".format(h, w)
    s3 = "Size: {0},{1}".format(h, w)
    return s1 + s2 + s3

def f():
    d1 = {}
    d1['name'] = "1"
    d2 = dict(name="2") 
    arr = [1,3,4,2]
    arr_new = sorted([1,3,4,2], key=lambda x: x[0]) 
    
if __name__ == "__main__":
    main()
"""

def main():
    # 1. 选择一个要分析的 python 文件

    # 2. 收集所有 SPT pattern 命中
    collector, module = collect_all_patterns(source)

    # 3. 打印统计信息
    print("=== SPT pattern 统计 ===")
    print(f"remove_unnecessary_else 命中数: {len(collector.remove_else_matches)}")
    print(f"loop_index_direct_reference 命中数: {len(collector.loop_index_matches)}")
    print(f"boolean_explicit_true_false 命中数: {len(collector.bool_explicit_matches)}")
    print(f"for_to_list_comprehension 命中数: {len(collector.for_listcomp_matches)}")

    # 4. 分别把每一条规则的命中打印出来（带上形态 original / transformed）
    # NL
    print("=== NL ===")
    print("\n--- naming_style ---")
    for idx, m in enumerate(collector.naming_style_matches, 1):
        print(f"[{idx}] style = {m.style.value}, name = {m.name_node.value}")
    
    # AL.expression
    print("\n=== AL.expression ===")
    print("\n--- boolean_explicit_true_false ---")
    for idx, m in enumerate(collector.bool_explicit_matches, 1):
        print(f"[{idx}] form = {m.form.value}")
        if m.form.name == "EXPLICIT_TRUE_FALSE":
            # 显式 True/False 形态：两者不同
            print("  full_expr :", module.code_for_node(m.value))
            print("  inner_expr:", module.code_for_node(m.inner_expr))
        else:
            # 直接布尔表达式形态：只打印一次就行
            print("  expr      :", module.code_for_node(m.inner_expr))
        print()

    print("\n--- condition_parentheses ---")
    for idx, m in enumerate(collector.condition_parens_matches, 1):
        print(f"[{idx}] form = {m.form.value}")
        print("  expr:", module.code_for_node(m.expr))
        print()
        
    print("\n--- dict_keys_usage ---")
    for idx, m in enumerate(collector.dict_keys_matches, 1):
        print(f"[{idx}] form = {m.form.value}")
        print("  expr:", module.code_for_node(m.comparison))
        print()
        
    print("\n--- format_percent_usage ---")
    for idx, m in enumerate(collector.format_percent_matches, 1):
        print(f"[{idx}] form = {m.form.value}")
        print("  expr:", module.code_for_node(m.expr))
        print()

    print("\n--- none_usage ---")
    for idx, m in enumerate(collector.none_usage_matches, 1):
        print(f"[{idx}] form = {m.form.value}")
        print("  expr:", module.code_for_node(m.expr))
        print()

    print("\n--- op_opequal_usage ---")
    for idx, m in enumerate(collector.op_opequal_usage_matches, 1):
        print(f"[{idx}] form = {m.form.name}")     # OP_EQUAL / OP_ASSIGN
        print(f"      op   = {m.op_kind.value}")  # add / sub / mul / div
        # 整条语句
        print("  stmt   :", module.code_for_node(m.stmt))
        # 目标变量（被更新的那个）
        print("  target :", module.code_for_node(m.target))
        # 增量/变化量表达式
        print("  delta  :", module.code_for_node(m.delta))
        print()
        
    print("\n--- parameter_default_sorted ---")
    for idx, m in enumerate(collector.parameter_default_sorted_matches, 1):
        print(f"[{idx}] form = {m.form.name}")  # NO_REVERSE / EXPLICIT_REVERSE_FALSE
        if m.form.name == "EXPLICIT_REVERSE_FALSE":
            print("  call (explicit) :", module.code_for_node(m.call))
        else:
            print("  call (implicit) :", module.code_for_node(m.call))
        print()

    # AL.block
    print("\n=== AL.block ===")
    print("\n--- for_to_list_comprehension ---")
    for idx, m in enumerate(collector.for_listcomp_matches, 1):
        print(f"[{idx}] form = {m.form.value}, target = {m.target_name}")
        print("  value_expr:", module.code_for_node(m.value_expr))
        print("  iter_expr: ", module.code_for_node(m.iter_expr))
        print("  assign stmt:")
        print(module.code_for_node(m.assign_stmt))
        if m.for_stmt is not None:
            print("  for stmt:")
            print(module.code_for_node(m.for_stmt))
        print()

    print("\n--- initialize_ways ---")
    for idx, m in enumerate(collector.initialize_ways_matches, 1):
        print(f"[{idx}] form = {m.form.value}")  # dict_call / empty_then_subscript

        if m.form.name == "DICT_CALL":
            # 单行 d = dict(...) 形态
            print("  stmt      :", module.code_for_node(m.first_stmt))
        else:
            # 两行 d = {}; d['name'] = ... 形态
            print("  first_stmt :", module.code_for_node(m.first_stmt))
            if m.second_stmt is not None:
                print("  second_stmt:", module.code_for_node(m.second_stmt))

        print("  target    :", module.code_for_node(m.target))

        if m.form.name == "EMPTY_THEN_SUBSCRIPT" and m.keys and m.values:
            print("  key       :", module.code_for_node(m.keys[0]))
            print("  value     :", module.code_for_node(m.values[0]))

        print()

    print("\n--- loop_index_direct_reference ---")
    for idx, m in enumerate(collector.loop_index_matches, 1):
        print(f"[{idx}] form = {m.form.value}, list = {m.list_name}")
        print(module.code_for_node(m.for_node))
        print()
    
    print("\n--- remove_unnecessary_else ---")
    for idx, m in enumerate(collector.remove_else_matches, 1):
        # m.form 是 ORIGINAL / TRANSFORMED
        # m.if_node 是整个 if 语句，可以用 .code 再渲染成源码片段
        print(f"[{idx}] form = {m.form.value}")
        print(module.code_for_node(m.if_node))
        print()


if __name__ == "__main__":
    main()