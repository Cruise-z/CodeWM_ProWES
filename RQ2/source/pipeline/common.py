from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable, List, Dict, Any, Optional


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def derive_seed(global_seed: int, sample_key: str, channel: str) -> int:
    payload = f"{global_seed}\0{sample_key}\0{channel}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:4], "big", signed=False)


def stable_uid(index: int, source: str) -> str:
    return f"rq2-{index:08d}-{sha256_text(source)[:12]}"


def read_jsonl(path: str | os.PathLike) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSONL at {path}:{lineno}: {e}") from e
    return out


def write_jsonl(path: str | os.PathLike, rows: Iterable[Dict[str, Any]]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def select_rows(rows: List[Dict[str, Any]], source_field: str, sample_size: Optional[int],
                max_chars: Optional[int], selection: str) -> List[Dict[str, Any]]:
    eligible = [r for r in rows if isinstance(r.get(source_field), str) and r.get(source_field)]
    if max_chars is not None:
        eligible = [r for r in eligible if len(r[source_field]) <= max_chars]
    if selection == "longest":
        eligible = sorted(eligible, key=lambda r: len(r[source_field]), reverse=True)
    elif selection != "input":
        raise ValueError(f"Unsupported selection: {selection}")
    if sample_size is not None:
        eligible = eligible[:sample_size]
    return eligible


def resolve_parser_lib(explicit: Optional[str], repo_root: Optional[str] = None) -> str:
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    env = os.environ.get("RQ2_TREE_SITTER_LIB")
    if env:
        candidates.append(Path(env))
    if repo_root:
        root = Path(repo_root)
        candidates += [root / "cStyleLang" / "parser" / "languages.so",
                       root / "parser" / "languages.so"]
    here = Path(__file__).resolve().parents[1]
    candidates += [here / "cStyleLang" / "parser" / "languages.so",
                   here / "project" / "srcMarker" / "SrcMarker" / "parser" / "languages.so"]
    for p in candidates:
        if p.exists():
            return str(p.resolve())
    raise FileNotFoundError(
        "Could not locate tree-sitter languages.so. Pass --parser-lib or set RQ2_TREE_SITTER_LIB."
    )
