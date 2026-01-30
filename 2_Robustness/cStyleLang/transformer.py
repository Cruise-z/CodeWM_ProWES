from typing import Optional, Sequence, Tuple, Dict, List
from cStyleCodeObfuscator.code_transform_provider import CodeTransformProvider
from cStyleCodeObfuscator.format import *  # preprocess_code, format_func
import tree_sitter

# -------------------------------
# 1) Runner（保留你的原始逻辑）
# -------------------------------
# class AutoFixedPipelineRunner:
#     """
#     - At init, compute transform key combinations via provider.get_transform_keys()
#     - Pick one combo automatically (default: the first combo)
#     - Later call transform(source_code) to apply that fixed combo.
#     """
#     def __init__(self, provider: CodeTransformProvider, combo_index: int = 0, validate: bool = True):
#         self.provider = provider
#         self._all_combos: Sequence[Tuple[str, ...]] = provider.get_transform_keys()
#         if not self._all_combos:
#             raise ValueError("No transform key combinations available.")
#         if combo_index < 0 or combo_index >= len(self._all_combos):
#             raise ValueError(f"combo_index out of range: {combo_index} (0..{len(self._all_combos)-1})")
#         self.selected_keys: Tuple[str, ...] = self._all_combos[combo_index]
#         # optional check that provider can run with these keys
#         if validate:
#             try:
#                 _ = self.provider.code_transform("void f(){}", self.selected_keys)
#             except Exception:
#                 # ignore; sanity check only (language might not be C++)
#                 pass

#     def transform(self, source_code: str, fail_silently: bool = True) -> str:
#         try:
#             return self.provider.code_transform(source_code, self.selected_keys)
#         except Exception:
#             if fail_silently:
#                 return source_code
#             raise

# --------------------------------------
# 2) 枚举“当前源码”的可执行变换（提取整合）
#    - 逻辑来自 collect_feasible_transforms_jsonl.py
# --------------------------------------
try:
    # 优先使用 utils 路径（与你的工程一致）
    from cStyleCodeObfuscator.mutable_tree.stringifiers import JavaScriptStringifier
    import cStyleCodeObfuscator.mutable_tree.transformers as ast_transformers
except Exception:
    # 退回裸包名（如果你的路径不是 utils 开头）
    from mutable_tree.stringifiers import JavaScriptStringifier
    import mutable_tree.transformers as ast_transformers  # noqa: F401  # 仅用于类型提示/示例

def _collect_tokens(root: tree_sitter.Node) -> List[str]:
    toks: List[str] = []
    def _walk(n: tree_sitter.Node):
        if n.child_count == 0:
            toks.append(n.text.decode())
        for ch in n.children:
            _walk(ch)
    _walk(root)
    return toks

def _wrap_for_lang(code: str, lang: str) -> str:
    # 与原脚本一致：Java 为了解析/比对加类包装；其它语言原样
    if lang == "java":
        return f"public class Test {{\n{code}\n}}"
    return code

def _normalize_js_wrapped(provider: CodeTransformProvider, code_wrapped: str, lang: str) -> str:
    # 与原脚本一致：JS 先 stringify 一次，减少无关格式差异
    if lang != "javascript":
        return code_wrapped
    try:
        mroot = provider.to_mutable_tree(code_wrapped)
        return JavaScriptStringifier().stringify(mroot)
    except Exception:
        return code_wrapped

def enumerate_feasible_keys_for_code(
    provider: CodeTransformProvider,
    parser: tree_sitter.Parser,
    transformers,  # List[CodeTransformer]
    lang: str,
    source_code: str,
) -> Dict[str, List[str]]:
    """
    返回: { transformer_name: [feasible_key, ...], ... }
    - 单 key 可行性：code_transform 成功 + 新旧 token 有变化 + 新代码可再次解析为 mutable_tree
    """
    per_tf_feasible: Dict[str, List[str]] = {}

    for t in transformers:
        t_name = t.name
        feasibles: List[str] = []
        keys = t.get_available_transforms()
        for key in keys:
            feasible = False
            # 1) 单 key 尝试
            try:
                new_code = provider.code_transform(source_code, [key])
            except Exception:
                continue  # 此 key 不可用

            # 2) 语法树 token 对比
            code_wrapped = _wrap_for_lang(source_code, lang)
            new_code_wrapped = _wrap_for_lang(new_code, lang)
            if lang == "javascript":
                code_wrapped = _normalize_js_wrapped(provider, code_wrapped, lang)

            code_tree = parser.parse(code_wrapped.encode("utf-8"))
            new_code_tree = parser.parse(new_code_wrapped.encode("utf-8"))

            # 3) 新代码可再次解析为 mutable_tree（语法有效）
            try:
                provider.to_mutable_tree(new_code)
            except Exception:
                feasible = False
                continue

            old_toks = _collect_tokens(code_tree.root_node)
            new_toks = _collect_tokens(new_code_tree.root_node)
            if len(old_toks) != len(new_toks):
                feasible = True
            else:
                for i in range(len(old_toks)):
                    if old_toks[i] != new_toks[i]:
                        feasible = True
                        break

            if feasible:
                feasibles.append(key)

        per_tf_feasible[t_name] = feasibles

    return per_tf_feasible

def enumerate_feasible_combos_for_code(
    provider: CodeTransformProvider,
    parser: tree_sitter.Parser,
    transformers,  # List[CodeTransformer]
    lang: str,
    source_code: str,
) -> List[Tuple[str, ...]]:
    """
    - 基于“当前源码”求每个变换器的可执行 keys；
    - 若某变换器无可执行 key，按原脚本逻辑补上它的“第一个理论 key”兜底；
    - 对各变换器 keys 做笛卡尔积，得到可执行组合（近似）。
    """
    per_tf = enumerate_feasible_keys_for_code(provider, parser, transformers, lang, source_code)

    # 兜底补全
    idict: Dict[str, List[str]] = {}
    for t in transformers:
        t_name = t.name
        theoreticals = list(t.get_available_transforms())
        feasibles = list(per_tf.get(t_name, []))
        if len(feasibles) < len(theoreticals):
            # 至少有一个不可行；补一个未出现过的理论 key
            for tt in theoreticals:
                if tt not in feasibles:
                    feasibles.append(tt)
                    break
        # 若理论 keys 为空（极少见），仍保证字典中有键
        if not feasibles and theoreticals:
            feasibles = [theoreticals[0]]
        idict[t_name] = feasibles

    # 笛卡尔积（按 transformers 顺序）
    combos: List[Tuple[str, ...]] = []
    def _dfs(i: int, cur: List[str]):
        if i == len(transformers):
            combos.append(tuple(cur))
            return
        t_name = transformers[i].name
        for k in idict[t_name]:
            _dfs(i + 1, cur + [k])
    _dfs(0, [])
    return combos

# --------------------------------------
# 3) Demo：构建 provider → 求可执行组合 → 选择并转换
# --------------------------------------
if __name__ == "__main__":
    # 1) parser
    LANG = "java"  # or "java" / "javascript"
    parser = tree_sitter.Parser()
    parser_lang = tree_sitter.Language("./parser/languages.so", LANG)
    parser.set_language(parser_lang)

    # 2) 选择要用的变换器（示例仅用你的 ReposVarDecl；需要可自行增删）
    code_transformers = [
        # NL:content 级别
        ast_transformers.IdRenameTransformer(),
        # ast_transformers.VarNameStyleTransformer(),
        # AL:expr 级别
        # ast_transformers.ReposVarDeclTransformer(),
        # ast_transformers.UpdateTransformer(),
        # ast_transformers.LoopCondTransformer(),
        # AL:block 级别
        # ast_transformers.LoopStmtTransformer(),
        # ast_transformers.IfFlatNestTransformer(),
        # ast_transformers.ConditionTransformer(),
        # ast_transformers.CondBlockSwapTransformer(),
    ]

    # 3) provider
    provider = CodeTransformProvider(LANG, parser, code_transformers)
    print("Total theoretical combos (cartesian product over transformers):",
          len(provider.get_transform_keys()))

    # 4) 准备一段源码（你可替换）
    source = r"""
public class example {
    public void testFunction(int input) {
        int a = 10;
        int b;
        b = input;
        int h;
        h = h + 1;
    }
}
"""

    source = r"""
public void testFunction(int input) {
    // sdjjdajdkl
    // int a = 10;         
    // int b = input;      
    // int h = 0;          
    // h = h + 1; 
    int a = 10;
    int b;
    b = input;
    int h;
    h = h + 1;         
}
"""

    source = r"""
public boolean blockingAwait(long timeout, TimeUnit unit) {
    // java 代码示例
    LinkedList < Cookie > m;
    m = 0;
    LinkedList < Cookie > n = 666;
    LinkedList < Cookie > x, y ,z = new LinkedList < Cookie > ( );
    x = 6;
    Throwable ex;
    y = 3;
    int j;
    x = cond ? a : b;
    if (getCount() != 0) {
        try {
            BlockingHelper.verifyNonBlocking();
            if (!await(timeout, unit)) {
                dispose();
                return false;
            }
        } catch (InterruptedException ex) {
            dispose();
            throw ExceptionHelper.wrapOrThrow(ex);
        }
    }
    if (z == 5){
        if (z == 5) {
            z+=1;
        }
        for (int i = 0; i < 10; i=i+1) {
            try{
                // some code
            } catch (Exception e) {
                // handle exception
                ex = error;
            }
        }
    }
    if (ex != null) {
        if (z == 5) {
            z+=1;
            throw ExceptionHelper.wrapOrThrow(ex);
        }
        else {
            z+=2;
        }
    }else{
        z+=3;
    }
    if (ex != null && z == 5) {
        z += 1;
        throw ExceptionHelper.wrapOrThrow(ex);
    }
    while(1){
        while(true){
            
        }
    }
    for(;;){
        for(;1;){
        }
    }
    return true;
}
"""
#     source = r"""
# public Playlist update ( TrackInfo Old , TrackInfo NewTrackInfo ) { List < TrackInfo > FINISHED = new ArrayList < > ( queue ) ; FINISHED.set ( FINISHED.indexOf ( Old ) , NewTrackInfo ) ; return new Playlist ( queue , name , playbackModes , position ) ; }
#     """

#     source = r"""
# bool blockingAwait(long long timeout, TimeUnit unit) {
#     // cpp代码示例
#     int m;
#     m = 0;
#     int n = 666;
#     int x, y, z = 0;
#     x = 6;
#     y = 3;

#     std::exception_ptr ex;  // 模拟 Java 的 Throwable ex;

#     int j = 0; // 未使用，但保留与原结构一致

#     if (getCount() != 0) {
#     }

#     if (z == 5) {
#         if (z == 5) {
#             z += 1;
#         }
#         for (int i = 0; i < 10; i++) {
#         }
#     }

#     if (ex) {
#         if (z == 5) {
#             z += 1;
#             ExceptionHelper::rethrow(ex);
#         }
#     }

#     while (1) {
#         while (true) {
#             if (z == 5) {
#                 break; // 仅跳出内层 while(true)
#             }
#         }
#         // 外层 while(1) 会无限循环；保持与原逻辑一致
#         break; // 为避免真正死循环，这里可选择跳出；如需与原版完全一致可移除这行
#     }

#     do {
#         // 保留原来的“z = z++;”语义（实际不会改变 z 的值）
#         z = z++;
#     } while (z != 5);

#     return true;
# }
# """

    # 5) 基于“当前源码”计算可执行组合（近似），并选一个组合来执行
    feasible_combos = enumerate_feasible_combos_for_code(
        provider=provider,
        parser=parser,
        transformers=code_transformers,
        lang=LANG,
        source_code=source,
    )
    print(f"# feasible combos for this source: {len(feasible_combos)}")
    for i, combo in enumerate(feasible_combos[:5]):
        print(f"[{i}] {combo}")

    # 选第 0 个可执行组合
    selected_keys = feasible_combos[0] if feasible_combos else provider.get_transform_keys()[0]

    # 6) 实际执行转换（直接用 provider；也可以把 Runner 扩展为接受 selected_keys）
    source_prep = preprocess_code(source)  # 你的预处理
    code_out = provider.code_transform(source_prep, selected_keys)
    print(code_out)

    # 7) 可选：格式化/落盘（保留你的接口用法）
    code_trans = format_func("test", code_out, LANG)
    print("\n===== Transformed Code =====\n")
    print(code_trans)
