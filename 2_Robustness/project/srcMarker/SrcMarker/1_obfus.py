#!/usr/bin/env python

from tqdm import tqdm
from argparse import ArgumentParser
from typing import Optional, Sequence, Tuple, Dict, List
from cStyleCodeObfuscator.code_transform_provider import CodeTransformProvider
from cStyleCodeObfuscator.format import *
import json
import re
import os
import time
import random
import subprocess
import textwrap
import tree_sitter

def count_lines_in_jsonl(file_path):
    # 执行 wc -l 命令
    result = subprocess.run(['wc', '-l', file_path], capture_output=True, text=True)
    
    # result.stdout 的格式为 '  1234 your_file.jsonl'，需要提取数字
    line_count = int(result.stdout.split()[0])
    return line_count

def parse_args():
    parser = ArgumentParser()
    parser.add_argument("--code_mxlen", type=int, default=3000)
    parser.add_argument("--sample", action="store_true", help="Enable sample mode")
    parser.add_argument("--sample_size", type=int, default=50)
    parser.add_argument("--result_dir", type=str, default="/home/zrz/Projects/GitRepo/Repo/Python_Projects/VSCode/Python/CodeWM_AutoTest/2_Robustness/project/srcMarker/obfusResult")
    return parser.parse_args()

def obfus(line:str, lang:str):
    from cStyleCodeObfuscator.mutable_tree.stringifiers import JavaScriptStringifier
    import cStyleCodeObfuscator.mutable_tree.transformers as ast_transformers
    
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
    
    # 1) parser setup
    parser = tree_sitter.Parser()
    # local
    # parser_lang = tree_sitter.Language("/home/zrz/Projects/GitRepo/Repo/Python_Projects/VSCode/Python/CodeWM_AutoTest/2_Robustness/cStyleLang/parser/languages.so", lang)
    #server
    parser_lang = tree_sitter.Language("/home/zrz/projects/Python_Projects/VSCode/Python/CodeWM_AutoTest/2_Robustness/cStyleLang/parser/languages.so", lang)
    parser.set_language(parser_lang)
    
    # 2) 选择要用的变换器（示例仅用你的 ReposVarDecl；需要可自行增删）
    code_transformers = [
        # NL:content 级别
        # ast_transformers.IdRenameTransformer(),
        # ast_transformers.VarNameStyleTransformer(),
        # AL:expr 级别
        # ast_transformers.ReposVarDeclTransformer(),
        # ast_transformers.UpdateTransformer(),
        # ast_transformers.LoopCondTransformer(),
        # AL:block 级别
        ast_transformers.LoopStmtTransformer(),
        ast_transformers.IfFlatNestTransformer(),
        ast_transformers.ConditionTransformer(),
        ast_transformers.CondBlockSwapTransformer(),
    ]

    # 3) provider
    provider = CodeTransformProvider(lang, parser, code_transformers)
    # print("Total theoretical combos (cartesian product over transformers):", len(provider.get_transform_keys()))
    
    data = json.loads(line)  # 解析 JSON 行
    if "after_watermark" in data:  # 确保 "test" 字段存在
        sourceCode = data["after_watermark"]
        
        try:
            # 5) 基于“当前源码”计算可执行组合（近似），并选一个组合来执行
            feasible_combos = enumerate_feasible_combos_for_code(
                provider=provider,
                parser=parser,
                transformers=code_transformers,
                lang=lang,
                source_code=sourceCode,
            )
            # print(f"# feasible combos for this source: {len(feasible_combos)}")
            # for i, combo in enumerate(feasible_combos[:5]):
            #     print(f"[{i}] {combo}")
                
            # 选第 0 个可执行组合
            selected_keys = feasible_combos[0] if feasible_combos else provider.get_transform_keys()[0]

            # 6) 实际执行转换（直接用 provider；也可以把 Runner 扩展为接受 selected_keys）
            source_prep = preprocess_code(sourceCode)  # 你的预处理
            code_obfus = provider.code_transform(source_prep, selected_keys)
            
            data["after_obfus"] = code_obfus
        except Exception as e:
            data["after_obfus"] = ''
            print(f'An error occurred, error: {e}')
        
        json_data = json.dumps(data, ensure_ascii=False)
        return json_data
    else:
        return None
    
#
# if you don't want to use Python module, you can import directly from the file
#
#from pelock.jobfuscator import JObfuscator


def main(args):
    MXLEN = args.code_mxlen
    SAMPLE = args.sample
    SSIZE = args.sample_size
    RESULT_DIR = args.result_dir
    
    #
    # source code in Java format
    #
    # 创建文件夹（如果已存在，则不会报错）
    # local
    # json_src = "/home/zrz/Projects/GitRepo/Repo/Python_Projects/VSCode/Python/CodeWM_AutoTest/2_Robustness/project/srcMarker/testResult/4bit_gru_srcmarker_42_csn_java_test.jsonl"
    # json_dest = "/home/zrz/Projects/GitRepo/Repo/Python_Projects/VSCode/Python/CodeWM_AutoTest/2_Robustness/project/srcMarker/obfusResult/4bit_gru_srcmarker_42_csn_java_obfus_ALL.jsonl"
    # server
    json_src = "/home/zrz/projects/Python_Projects/VSCode/Python/CodeWM_AutoTest/2_Robustness/project/srcMarker/testResult/4bit_gru_codemark_42_github_java_funcs_test.jsonl"
    json_dest = "/home/zrz/projects/Python_Projects/VSCode/Python/CodeWM_AutoTest/2_Robustness/project/srcMarker/obfusResult/4bit_gru_codemark_42_github_java_funcs_obfus_AL2.jsonl"
    os.makedirs(RESULT_DIR, exist_ok=True)
    #读取log计数文件中已经执行到的位置
    if os.path.exists(json_dest):
        cur_idx = count_lines_in_jsonl(json_dest)
    else:
        cur_idx = 0
    print(cur_idx)

    raw_lines = []
    with open(json_src, "r", encoding="utf-8") as f:
        for line in f:
            raw_lines.append(line)

    
    if SAMPLE:
        #若进行采样，则选取采样数据后进行混淆
        json_lines = sorted(
            (line for line in raw_lines if len(json.loads(line).get("after_watermark", "")) <= MXLEN),
            key=lambda x: len(json.loads(x).get("after_watermark", "")),
            reverse=True
        )
        json_lines = json_lines[:SSIZE]
    else:
        json_lines = raw_lines
    
    for idx, line in tqdm(enumerate(json_lines),
                          total=len(json_lines),
                          desc="Processing lines", 
                          unit="line"):
        if idx < cur_idx:
            continue
        json_data = obfus(line, lang="java")
        if json_data:
            with open(json_dest, "a", encoding="utf-8") as f:           
                f.write(json_data + '\n')
        # time.sleep(random.randint(1, 3))



if __name__ == "__main__":
    args = parse_args()
    main(args)