"""Small shared helpers for batch code generation."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Union


MAX_RESULT_DIR_COMPONENT_BYTES = 180

def read_file(path: Union[str, Path], encoding: str = "utf-8", errors: str = "strict") -> str:
    """Read a text file and return its content as a string."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"File not found or not a regular file: {p}")
    return p.read_text(encoding=encoding, errors=errors)


def _arg_value(args: dict, *keys, default=None):
    for key in keys:
        if key in args:
            return args[key]
    return default


def _shorten_path_component(name: str, *, max_bytes: int = MAX_RESULT_DIR_COMPONENT_BYTES) -> str:
    text = re.sub(r"[/\0]+", "_", str(name))
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    digest = hashlib.sha1(encoded).hexdigest()[:12]
    suffix = f"_h={digest}"
    separator = "_x_"
    budget = max(int(max_bytes) - len(suffix.encode("utf-8")), 16)
    tail_budget = min(48, max(budget // 3, 0))
    head_budget = max(budget - len(separator.encode("utf-8")) - tail_budget, 16)
    tail_budget = max(budget - len(separator.encode("utf-8")) - head_budget, 0)
    head = _utf8_prefix(text, head_budget).rstrip("_.-=")
    tail = _utf8_suffix(text, tail_budget).lstrip("_.-=")
    if tail:
        return f"{head}{separator}{tail}{suffix}"
    return f"{head}{suffix}"


def _utf8_prefix(text: str, max_bytes: int) -> str:
    chars: list[str] = []
    used = 0
    for ch in text:
        char_len = len(ch.encode("utf-8"))
        if used + char_len > max_bytes:
            break
        chars.append(ch)
        used += char_len
    return "".join(chars)


def _utf8_suffix(text: str, max_bytes: int) -> str:
    chars: list[str] = []
    used = 0
    for ch in reversed(text):
        char_len = len(ch.encode("utf-8"))
        if used + char_len > max_bytes:
            break
        chars.append(ch)
        used += char_len
    return "".join(reversed(chars))

def _nonempty(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_bool(value, default=False):
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "f", "no", "n", "off"}:
        return False
    return bool(default)


def _merge_nested_config(base: dict, extra):
    if not isinstance(extra, dict):
        return base
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key].update(value)
        else:
            base[key] = value
    return base
