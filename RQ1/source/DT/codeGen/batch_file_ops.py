"""Filesystem and shell helpers used by the batch runner."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Literal, Optional, Union

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
