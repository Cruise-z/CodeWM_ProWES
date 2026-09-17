"""Minimal inflection helpers used when the optional ``inflection`` package is absent.

This module intentionally implements only ``underscore`` and ``camelize`` because those
are the only helpers required by the bundled naming-style transformations.
"""
from __future__ import annotations
import re


def underscore(word: str) -> str:
    word = re.sub(r"::", "/", word)
    word = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", word)
    word = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", word)
    word = word.replace("-", "_")
    return word.lower()


def camelize(word: str, uppercase_first_letter: bool = True) -> str:
    parts = [p for p in re.split(r"_+", word) if p]
    if not parts:
        return ""
    head = parts[0]
    tail = "".join(p[:1].upper() + p[1:] for p in parts[1:])
    if uppercase_first_letter:
        head = head[:1].upper() + head[1:]
    else:
        head = head[:1].lower() + head[1:]
    return head + tail
