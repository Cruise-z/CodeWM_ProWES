#=====================================Basic environment setup=====================================#
import os, sys
import json
import re
import time
import hashlib
from typing import List, Any, Optional, Union, Literal
from difflib import SequenceMatcher
import shutil
import subprocess
from pathlib import Path
from decimal import Decimal
import asyncio
# os.chdir("/home/zhaorz/project/CodeWM/sweet-watermark/DT/workspace")

# 1) Route official OpenAI traffic through a proxy (adjust the port for your own proxy)
os.environ["HTTPS_PROXY"] = os.environ.get("HTTPS_PROXY", "http://127.0.0.1:7890")
os.environ["HTTP_PROXY"]  = os.environ.get("HTTP_PROXY",  "http://127.0.0.1:7890")
# Some environments read ALL_PROXY as well; set it consistently
os.environ["ALL_PROXY"]   = os.environ.get("ALL_PROXY",   os.environ["HTTPS_PROXY"])

# 2) Always bypass the proxy for loopback addresses (direct connection)
no_proxy = set(filter(None, os.environ.get("NO_PROXY", "").split(",")))
no_proxy.update({"127.0.0.1", "localhost", "::1"})
os.environ["NO_PROXY"] = ",".join(no_proxy)
os.environ["no_proxy"] = os.environ["NO_PROXY"]  # compatibility for lowercase
#=====================================Basic environment setup=====================================#

from agentCodeGen import codeGen, make_seed
from aiAPI import *

# Automated batch generation script
def read_file(path: Union[str, Path], encoding: str = "utf-8", errors: str = "strict") -> str:
    """Read a text file and return its content as a string."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"File not found or not a regular file: {p}")
    return p.read_text(encoding=encoding, errors=errors)

def find_path(
    root_abs: Path,
    matcher: Union[str, re.Pattern],
    *,
    kind: Literal["file", "dir", "any"] = "file",
    recursive: bool = False,
) -> Optional[Path]:
    """
    Find an entry under root_abs whose name matches `matcher`.

    - matcher:
        1) str: treated as suffix (e.g. ".java", ".log")
        2) re.Pattern: applied via fullmatch() to the entire name
    - kind:
        "file": only files
        "dir" : only directories
        "any" : files or directories
    - recursive:
        False: only search direct children of root_abs (non-recursive)
        True : search all descendants of root_abs (recursive)

    Return its absolute Path if found; otherwise None.
    If multiple matches exist, return the first one after sorting by path string.
    """
    root = Path(root_abs).resolve()
    if not root.is_dir():
        raise ValueError("root_abs must be an existing directory")

    if kind not in ("file", "dir", "any"):
        raise ValueError('kind must be one of: "file", "dir", "any"')

    iterator = root.rglob("*") if recursive else root.iterdir()

    matches = []
    for p in iterator:
        if kind == "file" and not p.is_file():
            continue
        if kind == "dir" and not p.is_dir():
            continue
        if kind == "any" and not (p.is_file() or p.is_dir()):
            continue

        name = p.name
        if isinstance(matcher, str):
            if name.endswith(matcher):
                matches.append(p)
        else:
            if matcher.fullmatch(name):
                matches.append(p)

    if not matches:
        return None

    # deterministic choice across recursive/non-recursive: sort by full path
    matches.sort(key=lambda x: str(x))
    return matches[0].resolve()

def shellPaste(sources, target):
    """
    Paste (copy) a list of directories/files into target like "copy -> paste" in file explorers:
    - Directories: merged into target/<dir_name>, files overwrite on name conflict
    - Files: copied into target (overwrite if same name exists)
    - Does NOT delete extra files in target (not a mirror sync)
    Depends on:
      - Windows: robocopy (built-in)
      - macOS/Linux: prefer rsync (commonly available), otherwise fallback to cp
    """
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)

    is_windows = os.name == "nt"
    has_rsync = shutil.which("rsync") is not None

    for src in map(Path, sources):
        if not src.exists():
            raise FileNotFoundError(f"{src} does not exist")

        if is_windows:
            # Windows: use robocopy (return codes 0–7 are considered success)
            if src.is_dir():
                dst = target / src.name
                cmd = [
                    "robocopy",
                    str(src),            # source directory
                    str(dst),            # destination directory (robocopy creates it)
                    "/E",                # recurse including empty dirs
                    "/R:0", "/W:0",      # no retries
                    "/NFL", "/NDL", "/NP" # reduce output noise
                ]
            else:
                # File: use robocopy with file filter to copy into target
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
                    f"robocopy failed (code {res.returncode})\n{res.stdout}\n{res.stderr}"
                )

        else:
            # macOS/Linux: prefer rsync; otherwise fallback to cp
            if src.is_dir():
                dst = target / src.name
                if has_rsync:
                    # Note the trailing slash semantics: src/ -> merge contents into dst/
                    dst.mkdir(parents=True, exist_ok=True)
                    cmd = ["rsync", "-aAX", str(src) + "/", str(dst) + "/"]
                else:
                    # cp -a: recursive + preserve attributes, overwrite
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
    Clear all contents inside a directory using system shell commands (do NOT remove the directory itself).
    - Windows: PowerShell Remove-Item
    - macOS/Linux: find + rm -rf
    - Dry-run mode (dry_run=True) prints what would be deleted without deleting

    Args:
        dir_path: directory path
        dry_run : True to only show what would be deleted

    May raise:
        FileNotFoundError, NotADirectoryError, RuntimeError
    """
    p = Path(dir_path).resolve()

    # Basic checks
    if not p.exists():
        raise FileNotFoundError(f"Path does not exist: {p}")
    if not p.is_dir():
        raise NotADirectoryError(f"Not a directory: {p}")

    # Safety guard: refuse to operate on root paths (e.g. "/" or "C:\\")
    def _is_root_like(path: Path) -> bool:
        return (os.name == "nt" and path == Path(path.anchor)) or (os.name != "nt" and str(path) == "/")

    if _is_root_like(p):
        raise RuntimeError(f"Refusing to wipe root path for safety: {p}")

    if os.name == "nt":
        # Windows: PowerShell
        pwsh = shutil.which("pwsh") or shutil.which("powershell")
        if not pwsh:
            raise RuntimeError("PowerShell not found. Install PowerShell or use Python shutil cleanup instead.")

        # Pass the path as an argument to avoid quoting/escaping issues
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
        # macOS / Linux: select all entries at depth=1, then rm -rf
        if dry_run:
            cmd = ["find", str(p), "-mindepth", "1", "-maxdepth", "1", "-print"]
        else:
            cmd = ["find", str(p), "-mindepth", "1", "-maxdepth", "1", "-exec", "rm", "-rf", "--", "{}", "+"]
        subprocess.run(cmd, check=True)

def get_programming_language(repoPath: Path) -> str:
    prd_dir = repoPath / "docs" / "prd"

    # Find files matching <number>.json
    candidates = [p for p in prd_dir.glob("*.json") if p.is_file() and p.stem.isdigit()]
    if not candidates:
        raise FileNotFoundError(f"No <number>.json file found under {prd_dir}.")

    # If multiple exist, pick the one with the largest number (usually a timestamp)
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
                raise ValueError(f"{target} line {idx} is not valid JSON: {e}") from e

            val = obj.get("Programming Language")
            if val is None:
                raise KeyError(f"{target} line {idx} is missing the 'Programming Language' field.")
            return re.sub(r"\d+", "", str(val)).replace("+", "p").replace(".", "")

    raise ValueError(f"{target} is empty or contains only blank lines.")

def remove_leading_h2_line(codeFilePath: Path, LANG: Optional[str] = None) -> list[Path]:
    """
    Remove one leading Markdown H2-style line from generated source files.

    If LANG is provided, only files matching the language postfix are touched,
    e.g. *.java for Java. This keeps snapshot comparison and cleanup aligned.
    If LANG is None, it falls back to scanning all files under codeFilePath.

    Note: if the leading '##...' line does NOT end with a newline, it will NOT be removed.
    """
    _PATTERN = re.compile(r"\A##[^\r\n]*\r?\n")
    modified: list[Path] = []
    encodings_try = ("utf-8", "utf-8-sig", "gb18030")  # common in CN environments; avoid latin-1 to reduce false edits

    root = Path(codeFilePath)
    if LANG is None:
        iterator = root.rglob("*")
    else:
        postfix = get_postfix(LANG)
        iterator = root.rglob(f"*.{postfix}")

    for p in iterator:
        if not p.is_file() or p.is_symlink():
            continue

        # Rough binary detection: skip if NUL byte exists
        try:
            with p.open("rb") as fb:
                head = fb.read(4096)
                if b"\x00" in head:
                    continue
                fb.seek(0)
                raw = fb.read()
        except Exception:
            continue  # skip unreadable files

        # Try decoding with multiple encodings
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
            continue  # treat as non-text/unknown encoding

        m = _PATTERN.match(text)
        if not m:
            continue  # no match at file start

        new_text = text[m.end():]

        # Write back; preserve permissions and (if any) BOM: utf-8-sig writeback keeps BOM
        try:
            p.write_text(new_text, encoding=used_encoding)
            modified.append(p)
        except Exception:
            # Ignore files that fail to write back
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
    elif LANG == "c++" or LANG == "cpp":
        return "cpp"
    else:
        raise ValueError(f"Unsupported programming language: {LANG}")

def snapshot_code_files(
    codeFilePath: Path,
    LANG: str,
) -> dict[str, str]:
    """
    Recursively snapshot generated source files under codeFilePath.

    The returned dict maps:
        relative/path/to/File.java -> sha256(content)

    For Java projects, codeFilePath may contain multiple .java files under
    src/main/java and src/test/java. If any Java file is added, removed, or
    changed, the snapshot will differ.
    """
    postfix = get_postfix(LANG)
    root = Path(codeFilePath).resolve()

    if not root.is_dir():
        raise NotADirectoryError(f"codeFilePath is not a directory: {root}")

    snapshot: dict[str, str] = {}

    for p in sorted(root.rglob(f"*.{postfix}"), key=lambda x: str(x)):
        if not p.is_file() or p.is_symlink():
            continue

        rel = p.relative_to(root).as_posix()
        content = p.read_bytes()
        snapshot[rel] = hashlib.sha256(content).hexdigest()

    if not snapshot:
        raise FileNotFoundError(f"Could not find any *.{postfix} files under {root}")

    return snapshot


def describe_snapshot_diff(
    prev_snapshot: dict[str, str],
    curr_snapshot: dict[str, str],
) -> str:
    """
    Return a compact human-readable summary of source snapshot differences.
    """
    prev_files = set(prev_snapshot)
    curr_files = set(curr_snapshot)

    added = sorted(curr_files - prev_files)
    removed = sorted(prev_files - curr_files)
    changed = sorted(
        p for p in (prev_files & curr_files)
        if prev_snapshot[p] != curr_snapshot[p]
    )

    parts = []
    if added:
        parts.append(f"added={added}")
    if removed:
        parts.append(f"removed={removed}")
    if changed:
        parts.append(f"changed={changed}")

    return "; ".join(parts) if parts else "no source changes"

def docker_exec(
    prev_code_snapshot: Optional[dict[str, str]],
    codeFilePath: Path,
    testFilePath: Path,
    LANG: str,
    desc: str,
) -> tuple[dict[str, str], int, bool]:
    """
    Clean generated source files, compare them with the previous source snapshot,
    and run docker tests only when the source code changed.

    Returns
    -------
    tuple[dict[str, str], int, bool]
        curr_code_snapshot, retCode, skipped
    """
    retCode = -1
    skipped = False
    curr_code_snapshot: dict[str, str] = {}

    try:
        remove_leading_h2_line(codeFilePath)
        curr_code_snapshot = snapshot_code_files(codeFilePath, LANG)

        if prev_code_snapshot is None:
            print(f"{desc} no previous code snapshot, skipping docker test")
            retCode = 0
            skipped = True
        else:
            if curr_code_snapshot == prev_code_snapshot:
                print(f"{desc} code unchanged, skipping docker test")
                retCode = 0
                skipped = True
            else:
                diff_summary = describe_snapshot_diff(prev_code_snapshot, curr_code_snapshot)
                print(f"{desc} code changed, running test: {diff_summary}")

                res = subprocess.run(
                    ["bash", testFilePath, codeFilePath],
                    env={
                        **os.environ,

                        # Maven proxy
                        "ENABLE_MAVEN_PROXY_CONFIG": "1",
                        "MAVEN_PROXY_HOST": "192.168.129.183",
                        "MAVEN_PROXY_PORT": "7897",

                        # Test timeout
                        "TEST_TIME_LIMIT": "30",

                        # Runtime check
                        "RUN_CHECK_SECONDS": "5",
                        "RUN_CHECK_KILL_AFTER": "2",

                        # Runtime output-loop detection
                        "RUNTIME_MAX_OUTPUT_BYTES": "262144",
                        "RUNTIME_MAX_OUTPUT_LINES": "200",
                        "RUNTIME_MAX_SAME_LINE": "30",
                        "RUNTIME_MAX_CONSECUTIVE_SAME_LINE": "10",

                        # Optional CPU busy-loop detection
                        "RUNTIME_ENABLE_CPU_BUSY_CHECK": "1",
                        "RUNTIME_CPU_BUSY_THRESHOLD": "95",
                        "RUNTIME_CPU_BUSY_MIN_SAMPLES": "6",
                    },
                    check=False,
                    text=True,
                    capture_output=True,
                )
                if res.stdout:
                    print(res.stdout)
                if res.stderr:
                    print(res.stderr, file=sys.stderr)
                retCode = res.returncode

    except Exception as e:
        print(e)

    return curr_code_snapshot, retCode, skipped

async def selectRngSeed(
    project_name: str, 
    srcPath: str, 
    workspacePath: str, 
    testFilePath: Path, 
    args: dict[str, Any],
    lang: Optional[Literal["cpp", "java", "python"]] = None,
) -> Optional[int]:

    repoPath = Path(f"{srcPath}/{project_name}").resolve()
    
    # Determine the programming language
    try:
        LANG = get_programming_language(repoPath)
    except:
        if lang is None:
            raise RuntimeError("Unable to auto-detect language; please pass lang explicitly.")
        LANG = lang
    LANG = LANG.lower()
    
    ckptPath = Path(f"{srcPath}/storage").resolve()
    codeFilePath = Path(f"{workspacePath}/{project_name}/{project_name}").resolve()
    
    while(1):
        seed = make_seed(32)
        seed = 1210046855

        xargs = {
            "temperature": args["temperature"],
            "max_tokens": args["max_tokens"],
            "rng_seed": seed,
            "internal_processor_names": [],
            "external_processor_names": [],
        }
        
        # 1) Clear the workspace
        shellDelete(workspacePath, dry_run=False)
        # 2) Copy project code into the workspace
        shellPaste([repoPath, ckptPath], workspacePath)
        # 3) Invoke code generation
        await codeGen(project_name, xargs)
        
        _, retCode, _ = docker_exec({"": ""}, codeFilePath, testFilePath, LANG, f"rngS={seed}")
        
        # time.sleep(20)
        
        if retCode == 0:
            return seed

def build_external_processor_params(args, wmS, LANG=None):
    processor = args["processor_names_ext"]
    delta = float(wmS)

    param_builders = {
        "sweet": lambda: {
            "gamma": args["gamma"],
            "delta": delta,
            "entropy_threshold": args["ET"],
            "z_threshold": args["z_threshold"],
        },
        "wllm": lambda: {
            "gamma": args["gamma"],
            "delta": delta,
            "z_threshold": args["z_threshold"],
        },
        "waterfall": lambda: {
            "id_mu": args["id_mu"],
            "k_p": args["k_p"],
            "kappa": delta,
            "n_gram": args["n_gram"],
            "wm_fn": args["wm_fn"],
            "auto_reset": args["auto_reset"],
            "detect_mode": args["detect_mode"],
        },
        "ewd": lambda: {
            "gamma": args["gamma"],
            "delta": delta,
            "hash_key": args["hash_key"],
            "z_threshold": args["z_threshold"],
            "prefix_length": args["prefix_length"],
        },
        "stone": lambda: {
            "gamma": args["gamma"],
            "delta": delta,
            "hash_key": args["hash_key"],
            "z_threshold": args["z_threshold"],
            "prefix_length": args["prefix_length"],
            "language": _require_lang(LANG, processor),
            "watermark_on_pl": args["watermark_on_pl"],
            "skipping_rule": args["skipping_rule"],
        },
        "codeip": lambda: {
            "mode": args["mode"],
            "delta": delta,
            "gamma": args["gamma"],
            "message_code_len": args["message_code_len"],
            "encode_ratio": args["encode_ratio"],
            "top_k": args["top_k"],
            "message": args["message"],
            "pda_model": None,
        },
    }

    if processor not in param_builders:
        raise ValueError(f"Unsupported processor_names_ext: {processor}")

    return param_builders[processor]()


def _require_lang(LANG, processor):
    if LANG is None:
        raise ValueError(f"processor_names_ext='{processor}' requires LANG")
    return LANG


def build_external_processor_config(args, wmS, LANG=None):
    processor = args["processor_names_ext"]

    return {
        "external_processor_names": [processor],
        "external_processor_params": {
            processor: build_external_processor_params(
                args=args,
                wmS=wmS,
                LANG=LANG,
            )
        },
    }

def build_result_dir(args, project_name, rng_seed, LANG=None):
    processor = args["processor_names_ext"]

    parts = [
        project_name,
        processor,
        f"T={args['temperature']}",
        f"rngS={rng_seed}",
    ]

    processor_fields = {
        "wllm": [
            ("gamma", "gamma"),
        ],
        "sweet": [
            ("gamma", "gamma"),
            ("ET", "ET"),
        ],
        "waterfall": [
            ("idMu", "id_mu"),
            ("kP", "k_p"),
            ("nGram", "n_gram"),
            ("wmFn", "wm_fn"),
        ],
        "ewd": [
            ("gamma", "gamma"),
            ("hashKey", "hash_key"),
            ("prefixLen", "prefix_length"),
        ],
        "stone": [
            ("gamma", "gamma"),
            ("hashKey", "hash_key"),
            ("prefixLen", "prefix_length"),
        ],
        "codeip": [
            ("gamma", "gamma"),
            ("mode", "mode"),
            ("messageLen", "message_code_len"),
            ("encodeRatio", "encode_ratio"),
            ("topK", "top_k"),
        ],
    }

    if processor not in processor_fields:
        raise ValueError(f"Unsupported processor_names_ext: {processor}")

    for label, key in processor_fields[processor]:
        parts.append(f"{label}={args[key]}")

    if processor == "stone":
        if LANG is None:
            raise ValueError("processor_names_ext='stone' requires LANG")
        parts.append(f"lang={LANG}")

    return "_".join(parts)

filterPrompt = """
Read the log above and output *ONLY* one [label] (no other text, eg: "[Pass]", "[Build Error]", etc):
 [Build Error]: The project fails during build or compilation related steps before tests can pass. Examples: Java Maven compile failure, C++ compile/link failure, dependency/build setup failure that prevents a successful build;
 [Test Error]: The project builds enough to run tests, but the required test step fails. Examples: failing assertions, test process errors, or `ctest` / `pytest` / `mvn test` failures caused by tests rather than by compilation;
 [Packaging Error]: The project passes tests, but fails when creating the required runnable artifact. Examples: `mvn package fails`, `Python zipapp creation fails`, or `no expected packaged executable/artifact is produced`;
 [Runtime Error]: The project passes tests and packaging, but the packaged artifact fails during the short execution check. Examples: the app crashes on startup, exits with an error, or cannot run successfully for the required short period;
 [Pass]: The project follows the protocol, passes the required tests, produces the expected packaged artifact, and the packaged artifact can start successfully in the short run check.
"""

async def codeGenBatch(
    rng_seed: int,
    project_name: str, 
    srcPath: str, 
    workspacePath: str, 
    resPath: str, 
    testFilePath: Path, 
    args: dict[str, Any],
    wmS_config: Optional[dict[str, str]] = None,
    lang: Optional[Literal["cpp", "java", "python"]] = None,
):
    client = Client("/home/zhaorz/.config/Personal_config/config_aiAPI.ini", "paid")

    repoPath = Path(f"{srcPath}/{project_name}").resolve()
    
    # Determine the programming language
    try:
        LANG = get_programming_language(repoPath)
    except:
        if lang is None:
            raise RuntimeError("Unable to auto-detect language; please pass lang explicitly.")
        LANG = lang
    LANG = LANG.lower()
    
    ckptPath = Path(f"{srcPath}/storage").resolve()
    codeFilePath = Path(f"{workspacePath}/{project_name}/{project_name}").resolve()
    
    if wmS_config is None:
        wmS = Decimal("0.0")
        step = Decimal("0.1")
        end = Decimal("15.0")

    wmS = Decimal(wmS_config["start"])
    step = Decimal(wmS_config["step"])
    end = Decimal(wmS_config["end"])
    
    prev_code_snapshot: Optional[dict[str, str]] = None

    # --- NEW: batch-level res aggregation (only increment when res is actually produced) ---
    ALLOWED_LABELS = ("[Build Error]", "[Test Error]", "[Packaging Error]", "[Runtime Error]", "[Pass]")
    batch_res_counts: dict[str, int] = {k: 0 for k in ALLOWED_LABELS}

    def _norm_label(x: Any) -> Optional[str]:
        s = str(x).strip().lower().rstrip(" .:;!?\n\t")
        scored = sorted(
            ((label, SequenceMatcher(None, s, label.lower()).ratio()) for label in ALLOWED_LABELS),
            key=lambda t: t[1],
            reverse=True,
        )
        best_label, best_score = scored[0]
        if best_score < 0.6:
            print(f"[WARN] Low-confidence label mapping: raw={x!r}, mapped={best_label!r}, score={best_score:.3f}")
            return None
        return best_label

    while wmS <= end:
        xargs = {
            "temperature": args["temperature"],
            "max_tokens": args["max_tokens"],
            # "parallel": args["parallel"],
            "rng_seed": rng_seed,
            "internal_processor_names": [],
            **build_external_processor_config(
                args=args,
                wmS=wmS,
                LANG=LANG,
            ),
        }
        
        # 1) Clear the workspace
        shellDelete(workspacePath, dry_run=False)
        # 2) Copy project code into the workspace
        shellPaste([repoPath, ckptPath], workspacePath)
        # 3) Invoke code generation
        await codeGen(project_name, xargs)

        # 4) Build output directory for this wmS
        result_dir = build_result_dir(args, project_name, rng_seed, LANG)
        destPath = Path(f"{resPath}/{result_dir}/{project_name}_{wmS}").resolve()
        os.makedirs(destPath, exist_ok=True)

        # 5) Remove leading H2 markers, compare source snapshots, and run docker only if code changed
        curr_code_snapshot, retCode, skipped = docker_exec(
            prev_code_snapshot,
            codeFilePath,
            testFilePath,
            LANG,
            f"wmS={wmS}",
        )

        # 6) Save the actual code that was compared/tested, after remove_leading_h2_line(...)
        shellPaste([codeFilePath], destPath)

        if skipped:
            # Source files are byte-for-byte identical to the previous wmS after cleanup.
            # Do not run docker, do not reuse/copy previous DTResults, and do not update result counts.
            print(f"[INFO] wmS={wmS} skipped docker test because source snapshot is unchanged.")

        else:
            DTResPath = (codeFilePath / "DTResults").resolve()
            if DTResPath.exists():
                try:
                    pat = re.compile(r"evaluation\.log")
                    logPath = find_path(DTResPath, pat, kind="file", recursive=True)
                    if logPath is None:
                        pat = re.compile(r"host_wrapper_\d{8}_\d{6}\.log")
                        logPath = find_path(DTResPath, pat, kind="file", recursive=True)
                    if logPath is not None:
                        print(f"[INFO] Using log file for classification: {logPath}")
                        logContent = read_file(logPath)
                        logContent += filterPrompt
                        res = common_chat(client, Model.gpt4o_240513, [logContent], StreamMode=True)
                        label = _norm_label(res)
                        if label is not None:
                            batch_res_counts[label] += 1
                        else:
                            print(f"[WARN] Unrecognized result label from model: {res!r}", file=sys.stderr)
                    else:
                        print(f"[WARN] No usable log file found under {DTResPath}", file=sys.stderr)

                except Exception as e:
                    print(f"[ERROR] Failed to filter DTResults: {e}")

                shellPaste([DTResPath], destPath)
            else:
                print(f"[WARN] {DTResPath} does not exist; skipping collection.", file=sys.stderr)

        if curr_code_snapshot:
            prev_code_snapshot = curr_code_snapshot

        print(f"wmS={wmS} results have been saved to {destPath}")

        wmS += step
    
    # Summary
    try:
        # if for some reason batch_result_dir was never set, fall back to resPath
        out_dir = Path(f"{resPath}/{result_dir}").resolve()
        os.makedirs(out_dir, exist_ok=True)
        summary_path = out_dir / f"{project_name}_batch_summary_rngS={rng_seed}.json"
        summary = {
            "project_name": project_name,
            "rng_seed": rng_seed,
            "language": LANG,
            "counts": batch_res_counts,
        }
        with open(summary_path, "w", encoding="utf-8") as sf:
            json.dump(summary, sf, ensure_ascii=False, indent=2)
        print(f"[INFO] Batch summary saved to {summary_path}")
    except Exception as e:
        print(f"[WARN] Failed to write batch summary: {e}")
    
if __name__ == "__main__":

    project_name = "tank_battle_game"

    srcPath = "/home/zhaorz/project/CodeWM/srcRepo/"
    workspacePath = "/home/zhaorz/project/CodeWM/MetaGPT/workspace"
    resPath = "/home/zhaorz/project/CodeWM/results"
    testFilePath = Path("/home/zhaorz/project/CodeWM/proWES/1_Availability/DT/dockerTest/test_podman.sh").resolve()
    
    args = {
        "temperature": 0.7,
        "max_tokens": 4096,
    }
    rng_seed = asyncio.run(selectRngSeed(project_name, srcPath, workspacePath, testFilePath, args))

    print(rng_seed)

    wmS_config = {
        "start": "0.0",
        "step": "0.1",
        "end": "6.0",
    }
    
    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
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
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args, wmS_config))
    
    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
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
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args, wmS_config))
    
    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
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
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args, wmS_config))

    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
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
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args, wmS_config))
    
    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
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
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args, wmS_config))
    
    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
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
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args, wmS_config))
    
    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
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
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args, wmS_config))
    
    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
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
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args, wmS_config))
    
    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
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
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args, wmS_config))

    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
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
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args, wmS_config))
    
    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
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
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args, wmS_config))
    
    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
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
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args, wmS_config))

    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
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
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args, wmS_config))
    
    # args = {
    #     "temperature": 0.7,
    #     "max_tokens": 4096,
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
    # asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args, wmS_config))
    
    args = {
        "temperature": 0.7,
        "max_tokens": 4096,
        "processor_names_ext": "stone",
        "gamma": 0.5,
        "ET": 0.85,
        "id_mu": 42,
        "k_p": 1,
        "n_gram": 2,
        "wm_fn": "fourier",
        "auto_reset": True,
        "detect_mode": "batch",
        "hash_key": 15485917,
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
    asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args, wmS_config))
    
    args = {
        "temperature": 0.7,
        "max_tokens": 4096,
        "processor_names_ext": "stone",
        "gamma": 0.5,
        "ET": 0.85,
        "id_mu": 42,
        "k_p": 1,
        "n_gram": 2,
        "wm_fn": "fourier",
        "auto_reset": True,
        "detect_mode": "batch",
        "hash_key": 23873851,
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
    asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args, wmS_config))
    
    args = {
        "temperature": 0.7,
        "max_tokens": 4096,
        "processor_names_ext": "stone",
        "gamma": 0.5,
        "ET": 0.85,
        "id_mu": 42,
        "k_p": 1,
        "n_gram": 2,
        "wm_fn": "fourier",
        "auto_reset": True,
        "detect_mode": "batch",
        "hash_key": 47646761,
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
    asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args, wmS_config))
    
    args = {
        "temperature": 0.7,
        "max_tokens": 4096,
        "processor_names_ext": "stone",
        "gamma": 0.5,
        "ET": 0.85,
        "id_mu": 42,
        "k_p": 1,
        "n_gram": 2,
        "wm_fn": "fourier",
        "auto_reset": True,
        "detect_mode": "batch",
        "hash_key": 36728353,
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
    asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args, wmS_config))

    args = {
        "temperature": 0.7,
        "max_tokens": 4096,
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
    asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args, wmS_config))

    wmS_config = {
        "start": "0.0",
        "step": "0.1",
        "end": "15.0",
    }
    
    args = {
        "temperature": 0.7,
        "max_tokens": 4096,
        "processor_names_ext": "waterfall",
        "gamma": 0.5,
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
    asyncio.run(codeGenBatch(rng_seed, project_name, srcPath, workspacePath, resPath, testFilePath, args, wmS_config))
