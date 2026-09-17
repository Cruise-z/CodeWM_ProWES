from typing import Optional, Sequence, Tuple, Dict, List
from cStyleCodeObfuscator.code_transform_provider import CodeTransformProvider
from cStyleCodeObfuscator.format import *  # preprocess_code, format_func
import tree_sitter

# -------------------------------
# 1) Runner (keep your original logic)
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
# 2) Enumerate executable transforms for the current source code
#    - Logic adapted from collect_feasible_transforms_jsonl.py
# --------------------------------------
try:
    # Prefer the utils path first, to stay aligned with your project layout
    from cStyleCodeObfuscator.mutable_tree.stringifiers import JavaScriptStringifier
    import cStyleCodeObfuscator.mutable_tree.transformers as ast_transformers
except Exception:
    # Fall back to bare package names if your path does not start with utils
    from mutable_tree.stringifiers import JavaScriptStringifier
    import mutable_tree.transformers as ast_transformers  # noqa: F401  # only for type hints/examples

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
    # Match the original script: wrap Java in a class for parsing/comparison; keep other languages unchanged
    if lang == "java":
        return f"public class Test {{\n{code}\n}}"
    return code

def _normalize_js_wrapped(provider: CodeTransformProvider, code_wrapped: str, lang: str) -> str:
    # Match the original script: stringify JS once first to reduce irrelevant formatting differences
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
    Returns: { transformer_name: [feasible_key, ...], ... }
    - A single key is feasible if code_transform succeeds, the old/new tokens differ, and the new code can be parsed again into mutable_tree
    """
    per_tf_feasible: Dict[str, List[str]] = {}

    for t in transformers:
        t_name = t.name
        feasibles: List[str] = []
        keys = t.get_available_transforms()
        for key in keys:
            feasible = False
            # 1) Try a single key
            try:
                new_code = provider.code_transform(source_code, [key])
            except Exception:
                continue  # This key is not usable

            # 2) Compare syntax-tree tokens
            code_wrapped = _wrap_for_lang(source_code, lang)
            new_code_wrapped = _wrap_for_lang(new_code, lang)
            if lang == "javascript":
                code_wrapped = _normalize_js_wrapped(provider, code_wrapped, lang)

            code_tree = parser.parse(code_wrapped.encode("utf-8"))
            new_code_tree = parser.parse(new_code_wrapped.encode("utf-8"))

            # 3) The new code can be parsed again into mutable_tree (syntactically valid)
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
    - Compute executable keys for each transformer from the current source code;
    - If a transformer has no executable key, use its first theoretical key as a fallback, following the original script;
    - Take the Cartesian product of all transformer keys to get executable combinations (approximately).
    """
    per_tf = enumerate_feasible_keys_for_code(provider, parser, transformers, lang, source_code)

    # Fallback completion
    idict: Dict[str, List[str]] = {}
    for t in transformers:
        t_name = t.name
        theoreticals = list(t.get_available_transforms())
        feasibles = list(per_tf.get(t_name, []))
        if len(feasibles) < len(theoreticals):
            # At least one key is infeasible; append a theoretical key that has not appeared yet
            for tt in theoreticals:
                if tt not in feasibles:
                    feasibles.append(tt)
                    break
        # Even if theoretical keys are empty (very rare), still keep the dictionary keyed
        if not feasibles and theoreticals:
            feasibles = [theoreticals[0]]
        idict[t_name] = feasibles

    # Cartesian product in transformer order
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
# 3) Demo: build the provider -> compute executable combinations -> choose one and transform
# --------------------------------------
if __name__ == "__main__":
    # 1) parser
    LANG = "java"  # or "java" / "javascript"
    parser = tree_sitter.Parser()
    parser_lang = tree_sitter.Language("./parser/languages.so", LANG)
    parser.set_language(parser_lang)

    # 2) Select the transformers to use (the example only uses your ReposVarDecl-style set; add or remove as needed)
    code_transformers = [
        # NL: content level
        ast_transformers.IdRenameTransformer(),
        # ast_transformers.VarNameStyleTransformer(),
        # AL: expression level
        # ast_transformers.ReposVarDeclTransformer(),
        # ast_transformers.UpdateTransformer(),
        # ast_transformers.LoopCondTransformer(),
        # AL: block level
        # ast_transformers.LoopStmtTransformer(),
        # ast_transformers.IfFlatNestTransformer(),
        # ast_transformers.ConditionTransformer(),
        # ast_transformers.CondBlockSwapTransformer(),
    ]

    # 3) provider
    provider = CodeTransformProvider(LANG, parser, code_transformers)
    print("Total theoretical combos (cartesian product over transformers):",
          len(provider.get_transform_keys()))

    # 4) Prepare a source snippet (replace it as needed)
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
    // Java code example
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
#     // C++ code example
#     int m;
#     m = 0;
#     int n = 666;
#     int x, y, z = 0;
#     x = 6;
#     y = 3;

#     std::exception_ptr ex;  // Simulates Java's Throwable ex;

#     int j = 0; // Unused, but kept to match the original structure

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
#                 break; // Only break out of the inner while(true)
#             }
#         }
#         // The outer while(1) would loop forever; kept consistent with the original logic
#         break; // To avoid a real infinite loop, you may break here; remove this line if exact original behavior is required
#     }

#     do {
#         // Preserve the original "z = z++;" semantics (it does not actually change the value of z)
#         z = z++;
#     } while (z != 5);

#     return true;
# }
# """

    # 5) Compute executable combinations for the current source (approximately) and choose one to execute
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

    # Select the first executable combination
    selected_keys = feasible_combos[0] if feasible_combos else provider.get_transform_keys()[0]

    # 6) Execute the transformation (directly with provider, or extend Runner to accept selected_keys)
    source_prep = preprocess_code(source)  # Your preprocessing
    code_out = provider.code_transform(source_prep, selected_keys)
    print(code_out)

    # 7) Optional: format / write to disk (keep your original interface usage)
    code_trans = format_func("test", code_out, LANG)
    print("\n===== Transformed Code =====\n")
    print(code_trans)
