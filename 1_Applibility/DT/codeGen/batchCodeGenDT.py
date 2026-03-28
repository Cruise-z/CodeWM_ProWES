#=====================================Basic Environment Setup=====================================#
import os, sys
import json
import re
import time
from typing import List, Any, Optional, Union
# os.chdir("/home/zhaorz/project/CodeWM/sweet-watermark/DT/workspace")

# 1) Route official OpenAI traffic through the proxy (adjust the port as needed)
os.environ["HTTPS_PROXY"] = os.environ.get("HTTPS_PROXY", "http://127.0.0.1:7890")
os.environ["HTTP_PROXY"]  = os.environ.get("HTTP_PROXY",  "http://127.0.0.1:7890")
# Some environments also read ALL_PROXY, so set it as well
os.environ["ALL_PROXY"]   = os.environ.get("ALL_PROXY",   os.environ["HTTPS_PROXY"])

# 2) Always bypass the proxy for local loopback addresses
no_proxy = set(filter(None, os.environ.get("NO_PROXY", "").split(",")))
no_proxy.update({"127.0.0.1", "localhost", "::1"})
os.environ["NO_PROXY"] = ",".join(no_proxy)
os.environ["no_proxy"] = os.environ["NO_PROXY"]  # Lowercase compatibility
#=====================================Basic Environment Setup=====================================#

import shutil
import subprocess
from pathlib import Path
from agentCodeGen import codeGen, make_seed
from decimal import Decimal
import asyncio
# Automated batch generation script
def read_file(path: Union[str, Path], encoding: str = "utf-8", errors: str = "strict") -> str:
    """Read a text file and return its content as a string."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"File not found or not a regular file: {p}")
    return p.read_text(encoding=encoding, errors=errors)

def find_file(root_abs: Path, suffix: str) -> Optional[Path]:
    """
    Search for a file under root_abs (non-recursively) whose name ends with suffix.
    Return its absolute Path if found; otherwise return None.
    If multiple matches exist, return the first after sorting by filename.
    """
    root = Path(root_abs).resolve()
    if not root.is_dir():
        raise ValueError("root_abs must be an existing directory")

    for f in sorted(root.iterdir()):
        if f.is_file() and f.name.endswith(suffix):
            return f.resolve()
    return None

def shellPaste(sources, target):
    """
    Paste multiple directories/files into target the way Explorer/Finder
    "copy -> paste" behaves:
    - Directories: merge into the same-named directory under target, overwriting files
    - Files: copy into target, overwriting files with the same name
    - Extra files already in target are not deleted (not a mirror copy)
    Dependencies:
      - Windows: robocopy (built in)
      - macOS/Linux: prefer rsync (commonly available), otherwise fall back to cp
    """
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)

    is_windows = os.name == "nt"
    has_rsync = shutil.which("rsync") is not None

    for src in map(Path, sources):
        if not src.exists():
            raise FileNotFoundError(f"{src} does not exist")

        if is_windows:
            # Windows: use robocopy consistently (0-7 are treated as success)
            if src.is_dir():
                dst = target / src.name
                cmd = [
                    "robocopy",
                    str(src),            # Source directory
                    str(dst),            # Destination directory (created automatically by robocopy)
                    "/E",                # Recurse and include empty directories
                    "/R:0", "/W:0",      # No retries
                    "/NFL", "/NDL", "/NP" # Reduce output verbosity
                ]
            else:
                # File: copy to the target using robocopy file filtering
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
                    f"robocopy failed (exit code {res.returncode})\n{res.stdout}\n{res.stderr}"
                )

        else:
            # macOS/Linux: prefer rsync; otherwise fall back to cp
            if src.is_dir():
                dst = target / src.name
                if has_rsync:
                    # Note the trailing slash semantics: src/ merges contents into dst/
                    dst.mkdir(parents=True, exist_ok=True)
                    cmd = ["rsync", "-aAX", str(src) + "/", str(dst) + "/"]
                else:
                    # cp -a: recursive copy while preserving attributes
                    cmd = ["cp", "-a", str(src), str(target)]
            else:
                if has_rsync:
                    cmd = ["rsync", "-aAX", str(src), str(target) + "/"]
                else:
                    cmd = ["cp", "-a", str(src), str(target)]

            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(
                    f"Copy failed: {' '.join(cmd)}\n{res.stdout}\n{res.stderr}"
                )

def shellDelete(dir_path: str, dry_run: bool = False) -> None:
    """
    Use system shell commands to clear all contents inside a directory
    without deleting the directory itself.
    - Windows: PowerShell Remove-Item
    - macOS/Linux: find + rm -rf
    - Provides a dry-run mode (dry_run=True) that only prints the entries
      that would be deleted

    Parameters:
        dir_path: directory path
        dry_run : if True, only show what would be deleted without actually deleting it

    May raise:
        FileNotFoundError, NotADirectoryError, SafetyError, RuntimeError
    """
    p = Path(dir_path).resolve()

    # Basic validation
    if not p.exists():
        raise FileNotFoundError(f"Path does not exist: {p}")
    if not p.is_dir():
        raise NotADirectoryError(f"Not a directory: {p}")

    # Safety guard: refuse to operate on a root path (for example "/" or "C:\\")
    def _is_root_like(path: Path) -> bool:
        return (os.name == "nt" and path == Path(path.anchor)) or (os.name != "nt" and str(path) == "/")

    if _is_root_like(p):
        raise RuntimeError(f"For safety reasons, refusing to clear a root path: {p}")

    if os.name == "nt":
        # Windows: PowerShell
        pwsh = shutil.which("pwsh") or shutil.which("powershell")
        if not pwsh:
            raise RuntimeError("PowerShell was not found. Install PowerShell or use Python shutil cleanup instead.")

        # Pass the path as an argument to avoid quote escaping issues
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
            raise RuntimeError(f"PowerShell execution failed ({res.returncode}):\n{res.stderr or res.stdout}")

    else:
        # macOS / Linux: use find to select all depth=1 entries, then rm -rf
        if dry_run:
            cmd = ["find", str(p), "-mindepth", "1", "-maxdepth", "1", "-print"]
        else:
            cmd = ["find", str(p), "-mindepth", "1", "-maxdepth", "1", "-exec", "rm", "-rf", "--", "{}", "+"]
        subprocess.run(cmd, check=True)

def get_programming_language(repoPath: Path) -> str:
    prd_dir = repoPath / "docs" / "prd"

    # Find files named like <number>.json
    candidates = [p for p in prd_dir.glob("*.json") if p.is_file() and p.stem.isdigit()]
    if not candidates:
        raise FileNotFoundError(f"No file matching <number>.json was found under {prd_dir}.")

    # If there are multiple candidates, take the one with the largest numeric stem
    target = max(candidates, key=lambda p: int(p.stem))

    # Read the first non-empty JSONL line and extract the field
    with target.open("r", encoding="utf-8-sig") as f:
        for idx, line in enumerate(f, 1):
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError as e:
                raise ValueError(f"Line {idx} in {target} is not valid JSON: {e}") from e

            val = obj.get("Programming Language")
            if val is None:
                raise KeyError(f"Line {idx} in {target} is missing the 'Programming Language' field.")
            return val

    raise ValueError(f"{target} is empty or only contains blank lines.")

def remove_leading_h2_line(codeFilePath: Path) -> list[Path]:
    """
    Traverse all files under codeFilePath. If the first line matches
    r'^##[^\\r\\n]*\\r?\\n', remove that line, write the file back,
    and return the list of modified files.
    Note: if the leading '##...' line has no trailing newline, it will not be removed.
    """
    _PATTERN = re.compile(r"\A##[^\r\n]*\r?\n")
    modified: list[Path] = []
    encodings_try = ("utf-8", "utf-8-sig", "gb18030")  # Compatible with common encodings; avoid latin-1 to reduce accidental binary corruption

    for p in Path(codeFilePath).rglob("*"):
        if not p.is_file() or p.is_symlink():
            continue

        # Rough binary detection: skip files containing NUL bytes
        try:
            with p.open("rb") as fb:
                head = fb.read(4096)
                if b"\x00" in head:
                    continue
                fb.seek(0)
                raw = fb.read()
        except Exception:
            continue  # Skip unreadable files

        # Try decoding with multiple encodings in order
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
            continue  # If decoding still fails, treat it as non-text/unknown encoding and skip

        m = _PATTERN.match(text)
        if not m:
            continue  # No match at the beginning, skip

        new_text = text[m.end():]

        # Write back; utf-8-sig preserves BOM if present
        try:
            p.write_text(new_text, encoding=used_encoding)
            modified.append(p)
        except Exception:
            # Ignore the file if writing back fails
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
        raise ValueError(f"Unsupported programming language: {LANG}")

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
            raise FileNotFoundError(f"Could not find a *_wm.{postfix} file")
        wmFilename = Path(curr_wmCodePath).name
        prefix = wmFilename.removesuffix(f"_wm.{postfix}")
        oriFilePath = Path(curr_wmCodePath).with_name(f"{prefix}.{postfix}")
        oriCode = read_file(oriFilePath).strip()
        curr_wmCode = read_file(curr_wmCodePath).strip()
        if curr_wmCode == (prev_wmCode if prev_wmCode else oriCode):
            print(f"{desc} code is unchanged, skipping the test")
            retCode = 0
        else:
            # Run the docker test script
            oriFilePath.write_text(curr_wmCode, encoding="utf-8")
            res = subprocess.run(
                ["bash", testFilePath, oriFilePath],
                check=False,
                text=True,
                capture_output=True,              # Capture stdout / stderr
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
    
    # Detect the programming language
    try:
        LANG = get_programming_language(repoPath)
    except:
        if lang is None:
            raise RuntimeError("Could not detect the programming language automatically. Please specify it via the lang argument.")
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
        
        # 1) Clear the workspace
        shellDelete(workspacePath, dry_run=False)
        # 2) Copy the project code into the workspace
        shellPaste([repoPath, ckptPath], workspacePath)
        # 3) Invoke code generation
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
    
    # Detect the programming language
    try:
        LANG = get_programming_language(repoPath)
    except:
        if lang is None:
            raise RuntimeError("Could not detect the programming language automatically. Please specify it via the lang argument.")
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
        
        # 1) Clear the workspace
        shellDelete(workspacePath, dry_run=False)
        # 2) Copy the project code into the workspace
        shellPaste([repoPath, ckptPath], workspacePath)
        # 3) Invoke code generation
        await codeGen(project_name, xargs)
        # 4) Save the generated results first
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
        
        # 5) Then check whether the watermark was embedded and run the docker test
        curr_wmCode = None
        curr_wmCode, retCode = docker_exec(prev_wmCode, codeFilePath, testFilePath, LANG, f"wmS={wmS}")
        
        DTResPath = (codeFilePath / "DTResults").resolve()
        if DTResPath.exists():
            shellPaste([DTResPath], destPath)
        else:
            print(f"[WARN] {DTResPath} does not exist, skipping collection.", file=sys.stderr)
        prev_wmCode = curr_wmCode
        print(f"wmS={wmS} results have been saved to {destPath}")
        
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
