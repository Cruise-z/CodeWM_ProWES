#=====================================基础环境配置=====================================#
import os, sys
import json
import re
import time
from typing import List, Any, Optional, Union
# os.chdir("/home/zhaorz/project/CodeWM/sweet-watermark/DT/workspace")

# 1) 让官方 OpenAI 走代理（按你的梯子改端口）
os.environ["HTTPS_PROXY"] = os.environ.get("HTTPS_PROXY", "http://127.0.0.1:7890")
os.environ["HTTP_PROXY"]  = os.environ.get("HTTP_PROXY",  "http://127.0.0.1:7890")
# 有些环境会读 ALL_PROXY，也统一设一下
os.environ["ALL_PROXY"]   = os.environ.get("ALL_PROXY",   os.environ["HTTPS_PROXY"])

# 2) 让本地回环地址永远直连（不走代理）
no_proxy = set(filter(None, os.environ.get("NO_PROXY", "").split(",")))
no_proxy.update({"127.0.0.1", "localhost", "::1"})
os.environ["NO_PROXY"] = ",".join(no_proxy)
os.environ["no_proxy"] = os.environ["NO_PROXY"]  # 兼容小写
#=====================================基础环境配置=====================================#

import shutil
import subprocess
from pathlib import Path
from agentCodeGen import codeGen, make_seed
from decimal import Decimal
import asyncio
# 自动化批量生成脚本
def read_file(path: Union[str, Path], encoding: str = "utf-8", errors: str = "strict") -> str:
    """读取文本文件内容并返回字符串。"""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"File not found or not a regular file: {p}")
    return p.read_text(encoding=encoding, errors=errors)

def find_file(root_abs: Path, suffix: str) -> Optional[Path]:
    """
    在 root_abs 目录下（不递归子目录）查找文件名以 suffix 结尾的文件，
    找到则返回其绝对 Path；未找到返回 None。
    若存在多个匹配，按文件名排序后返回第一个。
    """
    root = Path(root_abs).resolve()
    if not root.is_dir():
        raise ValueError("root_abs 必须是已存在的目录")

    for f in sorted(root.iterdir()):
        if f.is_file() and f.name.endswith(suffix):
            return f.resolve()
    return None

def shellPaste(sources, target):
    """
    像资源管理器/访达里“复制→粘贴”那样，把若干目录/文件粘到 target 下：
    - 目录：合并到 target 下的同名目录，文件会覆盖
    - 文件：复制到 target 下（同名覆盖）
    - 不会删除 target 中多余的文件（非镜像）
    依赖：
      - Windows：robocopy（自带）
      - macOS/Linux：优先 rsync（常见自带），否则退回 cp
    """
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)

    is_windows = os.name == "nt"
    has_rsync = shutil.which("rsync") is not None

    for src in map(Path, sources):
        if not src.exists():
            raise FileNotFoundError(f"{src} 不存在")

        if is_windows:
            # Windows：统一用 robocopy（0–7 都算成功）
            if src.is_dir():
                dst = target / src.name
                cmd = [
                    "robocopy",
                    str(src),            # 源目录
                    str(dst),            # 目标目录（robocopy 自动创建）
                    "/E",                # 递归包含空目录
                    "/R:0", "/W:0",      # 不重试
                    "/NFL", "/NDL", "/NP" # 少点输出
                ]
            else:
                # 文件：用 robocopy 的“文件筛选”复制到目标
                cmd = [
                    "robocopy",
                    str(src.parent),
                    str(target),
                    src.name,
                    "/R:0", "/W:0",
                    "/NFL", "/NDL", "/NP"
                ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode >= 8:
                raise RuntimeError(
                    f"robocopy 失败（返回码 {res.returncode}）\n{res.stdout}\n{res.stderr}"
                )

        else:
            # macOS/Linux：优先 rsync；否则退回 cp
            if src.is_dir():
                dst = target / src.name
                if has_rsync:
                    # 注意末尾斜杠的语义：src/ -> 把内容合并到 dst/
                    dst.mkdir(parents=True, exist_ok=True)
                    cmd = ["rsync", "-aAX", str(src) + "/", str(dst) + "/"]
                else:
                    # cp -Rfp：递归、保留属性、强制覆盖
                    cmd = ["cp", "-a", str(src), str(target)]
            else:
                if has_rsync:
                    cmd = ["rsync", "-aAX", str(src), str(target) + "/"]
                else:
                    cmd = ["cp", "-a", str(src), str(target)]

            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(
                    f"复制失败：{' '.join(cmd)}\n{res.stdout}\n{res.stderr}"
                )

def shellDelete(dir_path: str, dry_run: bool = False) -> None:
    """
    使用系统终端命令清空某目录内的所有内容（不删除该目录本身）。
    - Windows: PowerShell Remove-Item
    - macOS/Linux: find + rm -rf
    - 提供演练模式（dry_run=True）只打印将被删除的条目

    参数：
        dir_path: 目录路径
        dry_run : True 仅展示将删除的内容，不真正删除

    可能抛出：
        FileNotFoundError, NotADirectoryError, SafetyError, RuntimeError
    """
    p = Path(dir_path).resolve()

    # 基础检查
    if not p.exists():
        raise FileNotFoundError(f"路径不存在：{p}")
    if not p.is_dir():
        raise NotADirectoryError(f"不是文件夹：{p}")

    # 安全保护：拒绝对根路径操作（例如 "/" 或 "C:\\")
    def _is_root_like(path: Path) -> bool:
        return (os.name == "nt" and path == Path(path.anchor)) or (os.name != "nt" and str(path) == "/")

    if _is_root_like(p):
        raise RuntimeError(f"为安全起见，拒绝清空根路径：{p}")

    if os.name == "nt":
        # Windows：PowerShell
        pwsh = shutil.which("pwsh") or shutil.which("powershell")
        if not pwsh:
            raise RuntimeError("未找到 PowerShell，可安装 PowerShell 或改用 Python 的 shutil 清理。")

        # 通过参数传路径，避免引号转义问题
        script = (
            "$p=$args[0];"
            "if (-not (Test-Path -LiteralPath $p -PathType Container)) { throw 'Not a directory: ' + $p };"
            "if ($p -match '^[A-Za-z]:\\\\$') { throw 'Refusing to wipe drive root ' + $p };"
            "if ($args.Count -gt 1 -and $args[1] -eq 'dry') { "
            "  Get-ChildItem -LiteralPath $p -Force | Select-Object FullName | Out-Host; exit 0 "
            "} else { "
            "  Get-ChildItem -LiteralPath $p -Force | Remove-Item -Recurse -Force -ErrorAction Stop "
            "}"
        )
        argv = [pwsh, "-NoProfile", "-NonInteractive", "-Command", script, str(p)]
        if dry_run:
            argv.append("dry")
        res = subprocess.run(argv, text=True, capture_output=not dry_run)
        if res.returncode != 0:
            raise RuntimeError(f"PowerShell 执行失败（{res.returncode}）：\n{res.stderr or res.stdout}")

    else:
        # macOS / Linux：find 选中“深度=1”的所有条目，再 rm -rf
        if dry_run:
            cmd = ["find", str(p), "-mindepth", "1", "-maxdepth", "1", "-print"]
        else:
            cmd = ["find", str(p), "-mindepth", "1", "-maxdepth", "1", "-exec", "rm", "-rf", "--", "{}", "+"]
        subprocess.run(cmd, check=True)

def get_programming_language(repoPath: Path) -> str:
    prd_dir = repoPath / "docs" / "prd"

    # 找到形如 <数字>.json 的文件
    candidates = [p for p in prd_dir.glob("*.json") if p.is_file() and p.stem.isdigit()]
    if not candidates:
        raise FileNotFoundError(f"未在 {prd_dir} 下找到形如 <数字>.json 的文件。")

    # 如有多个，取数字（通常是时间戳）最大的那个
    target = max(candidates, key=lambda p: int(p.stem))

    # 读取首条非空 JSONL 并取出字段
    with target.open("r", encoding="utf-8-sig") as f:
        for idx, line in enumerate(f, 1):
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError as e:
                raise ValueError(f"{target} 第 {idx} 行不是合法 JSON：{e}") from e

            val = obj.get("Programming Language")
            if val is None:
                raise KeyError(f"{target} 第 {idx} 行缺少 'Programming Language' 字段。")
            return val

    raise ValueError(f"{target} 为空或只有空行。")

def remove_leading_h2_line(codeFilePath: Path) -> list[Path]:
    """
    遍历 codeFilePath 下所有文件，若文件开头的第一行匹配 r'^##[^\r\n]*\r?\n'，
    则删除该行并写回并返回被修改的文件列表。
    注意：若文件开头的 '##...' 行没有换行结尾, 将不会被删除.
    """
    _PATTERN = re.compile(r"\A##[^\r\n]*\r?\n")
    modified: list[Path] = []
    encodings_try = ("utf-8", "utf-8-sig", "gb18030")  # 兼容常见中文环境；最后不尝试 latin-1 以避免误改二进制

    for p in Path(codeFilePath).rglob("*"):
        if not p.is_file() or p.is_symlink():
            continue

        # 粗略二进制检测：存在 NUL 字节就跳过
        try:
            with p.open("rb") as fb:
                head = fb.read(4096)
                if b"\x00" in head:
                    continue
                fb.seek(0)
                raw = fb.read()
        except Exception:
            continue  # 无法读取就跳过

        # 依次尝试多种编码解码
        text = None
        used_encoding = None
        for enc in encodings_try:
            try:
                text = raw.decode(enc)
                used_encoding = enc
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            continue  # 实在解不了当作非文本/未知编码，跳过

        m = _PATTERN.match(text)
        if not m:
            continue  # 开头不匹配，跳过

        new_text = text[m.end():]

        # 写回；保留原文件权限与（若有）BOM：utf-8-sig 写回会带 BOM
        try:
            p.write_text(new_text, encoding=used_encoding)
            modified.append(p)
        except Exception:
            # 写回失败则忽略该文件
            continue

    return modified

def get_postfix(LANG: str) -> str:
    LANG = LANG.lower()
    if LANG == "python":
        return "py"
    elif LANG == "java":
        return "java"
    # elif LANG == "javascript":
    #     return "js"
    # elif LANG == "c++" or LANG == "cpp":
    #     return "cpp"
    else:
        raise ValueError(f"不支持的编程语言：{LANG}")

def docker_exec(
    prev_wmCode: Optional[str], 
    codeFilePath: Path, 
    testFilePath: Path,
    LANG: str, 
    desc:str
) -> tuple[str, int]:
    try:
        remove_leading_h2_line(codeFilePath)
        postfix = get_postfix(LANG)
        curr_wmCodePath = find_file(codeFilePath, f"_wm.{postfix}")
        if curr_wmCodePath is None:
            raise FileNotFoundError(f"未找到 *_wm.{postfix} 文件")
        wmFilename = Path(curr_wmCodePath).name
        prefix = wmFilename.removesuffix(f"_wm.{postfix}")
        oriFilePath = Path(curr_wmCodePath).with_name(f"{prefix}.{postfix}")
        oriCode = read_file(oriFilePath).strip()
        curr_wmCode = read_file(curr_wmCodePath).strip()
        if curr_wmCode == (prev_wmCode if prev_wmCode else oriCode):
            print(f"{desc} 代码无变化，跳过测试")
            retCode = 0
        else:
            # 运行docker test脚本
            oriFilePath.write_text(curr_wmCode, encoding="utf-8")
            res = subprocess.run(
                ["bash", testFilePath, oriFilePath],
                check=False,
                text=True,
                capture_output=True,              # 抓取 stdout / stderr
            )
            if res.stdout:
                print(res.stdout)
            if res.stderr:
                print(res.stderr, file=sys.stderr)
            retCode = res.returncode
    except Exception as e:
        print(e)
    return curr_wmCode, retCode

async def selectRngSeed(
    project_name: str, 
    srcPath: str, 
    workspacePath: str, 
    testFilePath: Path, 
    args: dict[str, Any],
    lang: Optional[str] = None,
) -> Optional[int]:

    repoPath = Path(f"{srcPath}/{project_name}").resolve()
    
    # 判断代码语言
    try:
        LANG = get_programming_language(repoPath)
    except:
        if lang is None:
            raise RuntimeError("无法自动识别编程语言，请传入 lang 参数指定。")
        LANG = lang
    LANG = LANG.lower()
    
    ckptPath = Path(f"{srcPath}/storage").resolve()
    codeFilePath = Path(f"{workspacePath}/{project_name}/{project_name}").resolve()
    
    while(1):
        seed = make_seed(32)
        seed = 4138137938

        xargs = {
            "temperature": args["temperature"],
            "max_tokens": args["max_tokens"],
            "rng_seed": seed,
            "internal_processor_names": [],
            "external_processor_names": [],
        }
        
        # 1) 清空工作区
        shellDelete(workspacePath, dry_run=False)
        # 2) 复制项目代码到工作区
        shellPaste([repoPath, ckptPath], workspacePath)
        # 3) 调用代码生成
        await codeGen(project_name, xargs)
        
        curr_wmCode, retCode = docker_exec("select rng_seed", codeFilePath, testFilePath, LANG, f"rngS={seed}")
        
        # time.sleep(20)
        
        if retCode == 0:
            return seed

async def codeGenBatch(
    rng_seed: int,
    project_name: str, 
    srcPath: str, 
    workspacePath: str, 
    resPath: str, 
    testFilePath: Path, 
    args: dict[str, Any],
    lang: Optional[str] = None,
):

    repoPath = Path(f"{srcPath}/{project_name}").resolve()
    
    # 判断代码语言
    try:
        LANG = get_programming_language(repoPath)
    except:
        if lang is None:
            raise RuntimeError("无法自动识别编程语言，请传入 lang 参数指定。")
        LANG = lang
    LANG = LANG.lower()
    
    ckptPath = Path(f"{srcPath}/storage").resolve()
    codeFilePath = Path(f"{workspacePath}/{project_name}/{project_name}").resolve()
    
    wmS = Decimal("0.0")
    step = Decimal("0.1")
    end = Decimal("15.0")
    
    prev_wmCode = None
    while wmS <= end:
        xargs = {
            "temperature": args["temperature"],
            "max_tokens": args["max_tokens"],
            "parallel": args["parallel"],
            "rng_seed": rng_seed,
            "internal_processor_names": [],
            "external_processor_names": [args["processor_names_ext"]],
            "external_processor_params": {
                "sweet": {
                    "gamma": args["gamma"], 
                    "delta": float(wmS), 
                    "entropy_threshold": args["ET"],
                    "z_threshold": args["z_threshold"],
                },
                "wllm": {
                    "gamma": args["gamma"], 
                    "delta": float(wmS),
                    "z_threshold": args["z_threshold"],
                },
                "waterfall": {
                    "id_mu": args["id_mu"], 
                    "k_p": args["k_p"], 
                    "kappa": float(wmS),
                    "n_gram": args["n_gram"], 
                    "wm_fn": args["wm_fn"],
                    "auto_reset": args["auto_reset"],
                    "detect_mode": args["detect_mode"],
                },
                "ewd": {
                    "gamma": args["gamma"],
                    "delta": float(wmS),
                    "hash_key": args["hash_key"],
                    "z_threshold": args["z_threshold"],
                    "prefix_length": args["prefix_length"],
                },
                "stone": {
                    "gamma": args["gamma"],
                    "delta": float(wmS),
                    "hash_key": args["hash_key"],
                    "z_threshold": args["z_threshold"],
                    "prefix_length": args["prefix_length"],
                    "language": LANG,
                    "watermark_on_pl": args["watermark_on_pl"],
                    "skipping_rule": args["skipping_rule"],
                },
                "codeip": {
                    "mode": args["mode"],
                    "delta": float(wmS),
                    "gamma": args["gamma"],
                    "message_code_len": args["message_code_len"],
                    "encode_ratio": args["encode_ratio"],
                    "top_k": args["top_k"],
                    "message": args["message"],
                    "pda_model": None,
                }
            },
        }
        
        # 1) 清空工作区
        shellDelete(workspacePath, dry_run=False)
        # 2) 复制项目代码到工作区
        shellPaste([repoPath, ckptPath], workspacePath)
        # 3) 调用代码生成
        await codeGen(project_name, xargs)
        # 4) 先保存生成结果
        if args["processor_names_ext"] == "wllm":
            result_dir = (
                f"{project_name}_"
                f"{args['processor_names_ext']}_"
                f"T={args['temperature']}_"
                f"rngS={rng_seed}_"
                f"gamma={args['gamma']}"
            )
        elif args["processor_names_ext"] == "sweet":
            result_dir = (
                f"{project_name}_"
                f"{args['processor_names_ext']}_"
                f"T={args['temperature']}_"
                f"rngS={rng_seed}_"
                f"gamma={args['gamma']}_"
                f"ET={args['ET']}"
            )
        elif args["processor_names_ext"] == "waterfall":
            result_dir = (
                f"{project_name}_"
                f"{args['processor_names_ext']}_"
                f"T={args['temperature']}_"
                f"rngS={rng_seed}_"
                f"idMu={args['id_mu']}_"
                f"kP={args['k_p']}_"
                f"nGram={args['n_gram']}_"
                f"wmFn={args['wm_fn']}"
            )
        elif args["processor_names_ext"] == "ewd":
            result_dir = (
                f"{project_name}_"
                f"{args['processor_names_ext']}_"
                f"T={args['temperature']}_"
                f"rngS={rng_seed}_"
                f"gamma={args['gamma']}_"
                f"hashKey={args['hash_key']}_"
                f"prefixLen={args['prefix_length']}"
            )
        elif args["processor_names_ext"] == "stone":
            result_dir = (
                f"{project_name}_"
                f"{args['processor_names_ext']}_"
                f"T={args['temperature']}_"
                f"rngS={rng_seed}_"
                f"gamma={args['gamma']}_"
                f"hashKey={args['hash_key']}_"
                f"prefixLen={args['prefix_length']}_"
                f"lang={LANG}"
            )
        elif args["processor_names_ext"] == "codeip":
            result_dir = (
                f"{project_name}_"
                f"{args['processor_names_ext']}_"
                f"T={args['temperature']}_"
                f"rngS={rng_seed}_"
                f"gamma={args['gamma']}_"
                f"mode={args['mode']}_"
                f"messageLen={args['message_code_len']}_"
                f"encodeRatio={args['encode_ratio']}_"
                f"topK={args['top_k']}"
            )
        destPath = Path(f"{resPath}/{result_dir}/{project_name}_{wmS}").resolve()
        os.makedirs(destPath, exist_ok=True)
        shellPaste([codeFilePath], destPath)
        
        # 5) 然后判断水印是否嵌入并进行docker test测试
        curr_wmCode = None
        curr_wmCode, retCode = docker_exec(prev_wmCode, codeFilePath, testFilePath, LANG, f"wmS={wmS}")
        
        DTResPath = (codeFilePath / "DTResults").resolve()
        if DTResPath.exists():
            shellPaste([DTResPath], destPath)
        else:
            print(f"[WARN] {DTResPath} 不存在，跳过回收。", file=sys.stderr)
        prev_wmCode = curr_wmCode
        print(f"wmS={wmS} 结果已保存到 {destPath}")
        
        wmS += step
    
if __name__ == "__main__":

    project_name = "tiny_calculator"

    srcPath = "/home/zhaorz/project/CodeWM/srcRepo/"
    workspacePath = "/home/zhaorz/project/CodeWM/MetaGPT/workspace"
    resPath = "/home/zhaorz/project/CodeWM/results"
    testFilePath = Path("/home/zhaorz/project/CodeWM/sweet-watermark/DT/dockerTest/test_podman.sh").resolve()
    
    args = {
        "temperature": 0.7,
        "max_tokens": 4096,
    }
    rng_seed = asyncio.run(selectRngSeed(project_name, srcPath, workspacePath, testFilePath, args))

    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
    #     "parallel": True,
    #     "processor_names_ext": "ewd",
    #     "gamma": 0.5,
    #     "ET": 0.85,
    #     "id_mu": 42,
    #     "k_p": 1,
    #     "n_gram": 2,
    #     "wm_fn": "fourier",
    #     "auto_reset": True,
    #     "detect_mode": "batch",
    #     "hash_key": 83782121,
    #     "prefix_length": 1,
    #     "watermark_on_pl": "False",
    #     "skipping_rule": "all_pl",
    #     "z_threshold": 4.0,
    #     "mode": "random",
    #     "message_code_len": 20,
    #     "encode_ratio": 10.0,
    #     "top_k": 1000,
    #     "message": [1,0,1,1,0,1,0,1,1,0,1,0,0,1,1,0,1,0,1,1],
    # }
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args))

    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
    #     "parallel": True,
    #     "processor_names_ext": "stone",
    #     "gamma": 0.5,
    #     "ET": 0.85,
    #     "id_mu": 42,
    #     "k_p": 1,
    #     "n_gram": 2,
    #     "wm_fn": "fourier",
    #     "auto_reset": True,
    #     "detect_mode": "batch",
    #     "hash_key": 83782121,
    #     "prefix_length": 1,
    #     "watermark_on_pl": "False",
    #     "skipping_rule": "all_pl",
    #     "z_threshold": 4.0,
    #     "mode": "random",
    #     "message_code_len": 20,
    #     "encode_ratio": 10.0,
    #     "top_k": 1000,
    #     "message": [1,0,1,1,0,1,0,1,1,0,1,0,0,1,1,0,1,0,1,1],
    # }
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args))
    
    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
    #     "parallel": True,
    #     "processor_names_ext": "ewd",
    #     "gamma": 0.5,
    #     "ET": 0.85,
    #     "id_mu": 42,
    #     "k_p": 1,
    #     "n_gram": 2,
    #     "wm_fn": "fourier",
    #     "auto_reset": True,
    #     "detect_mode": "batch",
    #     "hash_key": 15485863,
    #     "prefix_length": 1,
    #     "watermark_on_pl": "False",
    #     "skipping_rule": "all_pl",
    #     "z_threshold": 4.0,
    #     "mode": "random",
    #     "message_code_len": 20,
    #     "encode_ratio": 10.0,
    #     "top_k": 1000,
    #     "message": [1,0,1,1,0,1,0,1,1,0,1,0,0,1,1,0,1,0,1,1],
    # }
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args))
    
    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
    #     "parallel": True,
    #     "processor_names_ext": "stone",
    #     "gamma": 0.5,
    #     "ET": 0.85,
    #     "id_mu": 42,
    #     "k_p": 1,
    #     "n_gram": 2,
    #     "wm_fn": "fourier",
    #     "auto_reset": True,
    #     "detect_mode": "batch",
    #     "hash_key": 15485863,
    #     "prefix_length": 1,
    #     "watermark_on_pl": "False",
    #     "skipping_rule": "all_pl",
    #     "z_threshold": 4.0,
    #     "mode": "random",
    #     "message_code_len": 20,
    #     "encode_ratio": 10.0,
    #     "top_k": 1000,
    #     "message": [1,0,1,1,0,1,0,1,1,0,1,0,0,1,1,0,1,0,1,1],
    # }
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args))
    
    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
    #     "parallel": True,
    #     "processor_names_ext": "ewd",
    #     "gamma": 0.5,
    #     "ET": 0.85,
    #     "id_mu": 42,
    #     "k_p": 1,
    #     "n_gram": 2,
    #     "wm_fn": "fourier",
    #     "auto_reset": True,
    #     "detect_mode": "batch",
    #     "hash_key": 15485917,
    #     "prefix_length": 1,
    #     "watermark_on_pl": "False",
    #     "skipping_rule": "all_pl",
    #     "z_threshold": 4.0,
    #     "mode": "random",
    #     "message_code_len": 20,
    #     "encode_ratio": 10.0,
    #     "top_k": 1000,
    #     "message": [1,0,1,1,0,1,0,1,1,0,1,0,0,1,1,0,1,0,1,1],
    # }
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args))
    
    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
    #     "parallel": True,
    #     "processor_names_ext": "stone",
    #     "gamma": 0.5,
    #     "ET": 0.85,
    #     "id_mu": 42,
    #     "k_p": 1,
    #     "n_gram": 2,
    #     "wm_fn": "fourier",
    #     "auto_reset": True,
    #     "detect_mode": "batch",
    #     "hash_key": 15485917,
    #     "prefix_length": 1,
    #     "watermark_on_pl": "False",
    #     "skipping_rule": "all_pl",
    #     "z_threshold": 4.0,
    #     "mode": "random",
    #     "message_code_len": 20,
    #     "encode_ratio": 10.0,
    #     "top_k": 1000,
    #     "message": [1,0,1,1,0,1,0,1,1,0,1,0,0,1,1,0,1,0,1,1],
    # }
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args))
    
    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
    #     "parallel": True,
    #     "processor_names_ext": "ewd",
    #     "gamma": 0.5,
    #     "ET": 0.85,
    #     "id_mu": 42,
    #     "k_p": 1,
    #     "n_gram": 2,
    #     "wm_fn": "fourier",
    #     "auto_reset": True,
    #     "detect_mode": "batch",
    #     "hash_key": 23873851,
    #     "prefix_length": 1,
    #     "watermark_on_pl": "False",
    #     "skipping_rule": "all_pl",
    #     "z_threshold": 4.0,
    #     "mode": "random",
    #     "message_code_len": 20,
    #     "encode_ratio": 10.0,
    #     "top_k": 1000,
    #     "message": [1,0,1,1,0,1,0,1,1,0,1,0,0,1,1,0,1,0,1,1],
    # }
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args))
    
    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
    #     "parallel": True,
    #     "processor_names_ext": "stone",
    #     "gamma": 0.5,
    #     "ET": 0.85,
    #     "id_mu": 42,
    #     "k_p": 1,
    #     "n_gram": 2,
    #     "wm_fn": "fourier",
    #     "auto_reset": True,
    #     "detect_mode": "batch",
    #     "hash_key": 23873851,
    #     "prefix_length": 1,
    #     "watermark_on_pl": "False",
    #     "skipping_rule": "all_pl",
    #     "z_threshold": 4.0,
    #     "mode": "random",
    #     "message_code_len": 20,
    #     "encode_ratio": 10.0,
    #     "top_k": 1000,
    #     "message": [1,0,1,1,0,1,0,1,1,0,1,0,0,1,1,0,1,0,1,1],
    # }
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args))
    
    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
    #     "parallel": True,
    #     "processor_names_ext": "ewd",
    #     "gamma": 0.5,
    #     "ET": 0.85,
    #     "id_mu": 42,
    #     "k_p": 1,
    #     "n_gram": 2,
    #     "wm_fn": "fourier",
    #     "auto_reset": True,
    #     "detect_mode": "batch",
    #     "hash_key": 47646761,
    #     "prefix_length": 1,
    #     "watermark_on_pl": "False",
    #     "skipping_rule": "all_pl",
    #     "z_threshold": 4.0,
    #     "mode": "random",
    #     "message_code_len": 20,
    #     "encode_ratio": 10.0,
    #     "top_k": 1000,
    #     "message": [1,0,1,1,0,1,0,1,1,0,1,0,0,1,1,0,1,0,1,1],
    # }
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args))
    
    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
    #     "parallel": True,
    #     "processor_names_ext": "stone",
    #     "gamma": 0.5,
    #     "ET": 0.85,
    #     "id_mu": 42,
    #     "k_p": 1,
    #     "n_gram": 2,
    #     "wm_fn": "fourier",
    #     "auto_reset": True,
    #     "detect_mode": "batch",
    #     "hash_key": 47646761,
    #     "prefix_length": 1,
    #     "watermark_on_pl": "False",
    #     "skipping_rule": "all_pl",
    #     "z_threshold": 4.0,
    #     "mode": "random",
    #     "message_code_len": 20,
    #     "encode_ratio": 10.0,
    #     "top_k": 1000,
    #     "message": [1,0,1,1,0,1,0,1,1,0,1,0,0,1,1,0,1,0,1,1],
    # }
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args))
    
    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
    #     "parallel": True,
    #     "processor_names_ext": "ewd",
    #     "gamma": 0.5,
    #     "ET": 0.85,
    #     "id_mu": 42,
    #     "k_p": 1,
    #     "n_gram": 2,
    #     "wm_fn": "fourier",
    #     "auto_reset": True,
    #     "detect_mode": "batch",
    #     "hash_key": 36728353,
    #     "prefix_length": 1,
    #     "watermark_on_pl": "False",
    #     "skipping_rule": "all_pl",
    #     "z_threshold": 4.0,
    #     "mode": "random",
    #     "message_code_len": 20,
    #     "encode_ratio": 10.0,
    #     "top_k": 1000,
    #     "message": [1,0,1,1,0,1,0,1,1,0,1,0,0,1,1,0,1,0,1,1],
    # }
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args))
    
    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
    #     "parallel": True,
    #     "processor_names_ext": "stone",
    #     "gamma": 0.5,
    #     "ET": 0.85,
    #     "id_mu": 42,
    #     "k_p": 1,
    #     "n_gram": 2,
    #     "wm_fn": "fourier",
    #     "auto_reset": True,
    #     "detect_mode": "batch",
    #     "hash_key": 36728353,
    #     "prefix_length": 1,
    #     "watermark_on_pl": "False",
    #     "skipping_rule": "all_pl",
    #     "z_threshold": 4.0,
    #     "mode": "random",
    #     "message_code_len": 20,
    #     "encode_ratio": 10.0,
    #     "top_k": 1000,
    #     "message": [1,0,1,1,0,1,0,1,1,0,1,0,0,1,1,0,1,0,1,1],
    # }
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args))

    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
    #     "parallel": True,
    #     "rng_seed": 4138137938,
    #     "processor_names_ext": "sweet",
    #     "gamma": 0.1,
    #     "ET": 0.5,
    #     "id_mu": 42,
    #     "k_p": 1,
    #     "n_gram": 2,
    #     "wm_fn": "fourier",
    #     "auto_reset": True,
    #     "detect_mode": "batch",
    #     "hash_key": 15485863,
    #     "prefix_length": 1,
    #     "watermark_on_pl": "False",
    #     "skipping_rule": "all_pl",
    #     "z_threshold": 4.0,
    #     "mode": "random",
    #     "message_code_len": 20,
    #     "encode_ratio": 10.0,
    #     "top_k": 1000,
    #     "message": [1,0,1,1,0,1,0,1,1,0,1,0,0,1,1,0,1,0,1,1],
    # }
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args))
    
    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
    #     "parallel": True,
    #     "rng_seed": 4138137938,
    #     "processor_names_ext": "sweet",
    #     "gamma": 0.25,
    #     "ET": 0.5,
    #     "id_mu": 42,
    #     "k_p": 1,
    #     "n_gram": 2,
    #     "wm_fn": "fourier",
    #     "auto_reset": True,
    #     "detect_mode": "batch",
    #     "hash_key": 15485863,
    #     "prefix_length": 1,
    #     "watermark_on_pl": "False",
    #     "skipping_rule": "all_pl",
    #     "z_threshold": 4.0,
    #     "mode": "random",
    #     "message_code_len": 20,
    #     "encode_ratio": 10.0,
    #     "top_k": 1000,
    #     "message": [1,0,1,1,0,1,0,1,1,0,1,0,0,1,1,0,1,0,1,1],
    # }
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args))
    
    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
    #     "parallel": True,
    #     "rng_seed": 4138137938,
    #     "processor_names_ext": "sweet",
    #     "gamma": 0.5,
    #     "ET": 0.5,
    #     "id_mu": 42,
    #     "k_p": 1,
    #     "n_gram": 2,
    #     "wm_fn": "fourier",
    #     "auto_reset": True,
    #     "detect_mode": "batch",
    #     "hash_key": 15485863,
    #     "prefix_length": 1,
    #     "watermark_on_pl": "False",
    #     "skipping_rule": "all_pl",
    #     "z_threshold": 4.0,
    #     "mode": "random",
    #     "message_code_len": 20,
    #     "encode_ratio": 10.0,
    #     "top_k": 1000,
    #     "message": [1,0,1,1,0,1,0,1,1,0,1,0,0,1,1,0,1,0,1,1],
    # }
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args))
    
    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
    #     "parallel": True,
    #     "rng_seed": 4138137938,
    #     "processor_names_ext": "wllm",
    #     "gamma": 0.1,
    #     "ET": 0.5,
    #     "id_mu": 42,
    #     "k_p": 1,
    #     "n_gram": 2,
    #     "wm_fn": "fourier",
    #     "auto_reset": True,
    #     "detect_mode": "batch",
    #     "hash_key": 15485863,
    #     "prefix_length": 1,
    #     "watermark_on_pl": "False",
    #     "skipping_rule": "all_pl",
    #     "z_threshold": 4.0,
    #     "mode": "random",
    #     "message_code_len": 20,
    #     "encode_ratio": 10.0,
    #     "top_k": 1000,
    #     "message": [1,0,1,1,0,1,0,1,1,0,1,0,0,1,1,0,1,0,1,1],
    # }
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args))
    
    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
    #     "parallel": True,
    #     "rng_seed": 4138137938,
    #     "processor_names_ext": "wllm",
    #     "gamma": 0.25,
    #     "ET": 0.5,
    #     "id_mu": 42,
    #     "k_p": 1,
    #     "n_gram": 2,
    #     "wm_fn": "fourier",
    #     "auto_reset": True,
    #     "detect_mode": "batch",
    #     "hash_key": 15485863,
    #     "prefix_length": 1,
    #     "watermark_on_pl": "False",
    #     "skipping_rule": "all_pl",
    #     "z_threshold": 4.0,
    #     "mode": "random",
    #     "message_code_len": 20,
    #     "encode_ratio": 10.0,
    #     "top_k": 1000,
    #     "message": [1,0,1,1,0,1,0,1,1,0,1,0,0,1,1,0,1,0,1,1],
    # }
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args))
    
    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
    #     "parallel": True,
    #     "rng_seed": 4138137938,
    #     "processor_names_ext": "wllm",
    #     "gamma": 0.5,
    #     "ET": 0.5,
    #     "id_mu": 42,
    #     "k_p": 1,
    #     "n_gram": 2,
    #     "wm_fn": "fourier",
    #     "auto_reset": True,
    #     "detect_mode": "batch",
    #     "hash_key": 15485863,
    #     "prefix_length": 1,
    #     "watermark_on_pl": "False",
    #     "skipping_rule": "all_pl",
    #     "z_threshold": 4.0,
    #     "mode": "random",
    #     "message_code_len": 20,
    #     "encode_ratio": 10.0,
    #     "top_k": 1000,
    #     "message": [1,0,1,1,0,1,0,1,1,0,1,0,0,1,1,0,1,0,1,1],
    # }
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args))
    
    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
    #     "parallel": True,
    #     "rng_seed": 4138137938,
    #     "processor_names_ext": "waterfall",
    #     "gamma": 0.5,
    #     "ET": 0.5,
    #     "id_mu": 42,
    #     "k_p": 1,
    #     "n_gram": 2,
    #     "wm_fn": "fourier",
    #     "auto_reset": True,
    #     "detect_mode": "batch",
    #     "hash_key": 15485863,
    #     "prefix_length": 1,
    #     "watermark_on_pl": "False",
    #     "skipping_rule": "all_pl",
    #     "z_threshold": 4.0,
    #     "mode": "random",
    #     "message_code_len": 20,
    #     "encode_ratio": 10.0,
    #     "top_k": 1000,
    #     "message": [1,0,1,1,0,1,0,1,1,0,1,0,0,1,1,0,1,0,1,1],
    # }
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args))
    
    args = {
        "temperature": 0.7,
        "max_tokens": 4096,
        "parallel": True,
        "rng_seed": 4138137938,
        "processor_names_ext": "codeip",
        "gamma": 3,
        "ET": 0.5,
        "id_mu": 42,
        "k_p": 1,
        "n_gram": 2,
        "wm_fn": "fourier",
        "auto_reset": True,
        "detect_mode": "batch",
        "hash_key": 15485863,
        "prefix_length": 1,
        "watermark_on_pl": "False",
        "skipping_rule": "all_pl",
        "z_threshold": 4.0,
        "mode": "random",
        "message_code_len": 20,
        "encode_ratio": 10.0,
        "top_k": 1000,
        "message": [1,0,1,1,0,1,0,1,1,0,1,0,0,1,1,0,1,0,1,1],
    }
    asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args))