# pyCodeObfuscator/patterns/NL/naming_style_pattern.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

import keyword
import libcst as cst


class NamingStyle(str, Enum):
    CAMEL = "camel"                 # UserAddNum
    SNAKE = "snake"                 # user_add_num
    PASCAL_UNDERSCORE = "pascal_underscore"  # user_Add_Num


@dataclass
class NamingStyleMatch:
    style: NamingStyle
    name_node: cst.Name
    words: List[str]  # Represent uniformly as a lowercase word sequence, for example ["user", "add", "num"]


_PY_KEYWORDS = set(keyword.kwlist)
_PY_CONSTANTS = {"True", "False", "None"}


def _is_valid_identifier(name: str) -> bool:
    # Basic filtering: valid identifier, not a keyword, and not True/False/None
    if not name.isidentifier():
        return False
    if name in _PY_KEYWORDS or name in _PY_CONSTANTS:
        return False
    return True


def _split_snake(name: str) -> Optional[List[str]]:
    """
    user_add_num
    """
    if "_" not in name:
        return None
    if not name[0].isalpha():
        return None
    if not all(ch.islower() or ch.isdigit() or ch == "_" for ch in name):
        return None

    parts = name.split("_")
    if any(not part for part in parts):
        return None
    if any(not p[0].isalpha() for p in parts):
        return None

    # Normalize to lowercase words
    return [p.lower() for p in parts]


def _split_camel(name: str) -> Optional[List[str]]:
    """
    UserAddNum  (following your example, Camel / Pascal with an uppercase first letter)
    """
    if "_" in name:
        return None
    if not name[0].isupper():
        return None
    if not name.isalnum():
        return None

    words: List[str] = []
    start = 0
    for i in range(1, len(name)):
        if name[i].isupper():
            words.append(name[start:i].lower())
            start = i
    words.append(name[start:].lower())

    if any(not w for w in words):
        return None
    return words


def _split_pascal_underscore(name: str) -> Optional[List[str]]:
    """
    user_Add_Num
      - First segment: all lowercase
      - Following segments: uppercase first letter, lowercase remainder
    """
    if "_" not in name:
        return None
    parts = name.split("_")
    if any(not p for p in parts):
        return None
    first = parts[0]
    rest = parts[1:]

    if not first.isalpha() or not first.islower():
        return None

    for p in rest:
        if not p.isalpha():
            return None
        if not (p[0].isupper() and p[1:].islower()):
            return None

    words = [first.lower()] + [p.lower() for p in rest]
    return words


def match_naming_style(name_node: cst.Name) -> Optional[NamingStyleMatch]:
    """
    Perform naming-style matching only on cst.Name.
    Return the style plus the word sequence; if it is not one of these three styles, return None.
    """
    name = name_node.value

    if not _is_valid_identifier(name):
        return None

    # Check snake first, then user_Add_Num, then UserAddNum
    words = _split_snake(name)
    if words is not None:
        return NamingStyleMatch(
            style=NamingStyle.SNAKE,
            name_node=name_node,
            words=words,
        )

    words = _split_pascal_underscore(name)
    if words is not None:
        return NamingStyleMatch(
            style=NamingStyle.PASCAL_UNDERSCORE,
            name_node=name_node,
            words=words,
        )

    words = _split_camel(name)
    if words is not None:
        return NamingStyleMatch(
            style=NamingStyle.CAMEL,
            name_node=name_node,
            words=words,
        )

    return None


def build_name(style: NamingStyle, words: List[str]) -> str:
    """
    Construct an identifier string in a target style from a normalized lowercase word sequence.
    """
    if style is NamingStyle.SNAKE:
        return "_".join(words)

    if style is NamingStyle.CAMEL:
        # UserAddNum
        return "".join(w.capitalize() for w in words)

    if style is NamingStyle.PASCAL_UNDERSCORE:
        # user_Add_Num
        if not words:
            return ""
        first = words[0].lower()
        rest = [w.capitalize() for w in words[1:]]
        return "_".join([first] + rest)

    # This path should not be reached in theory
    return "_".join(words)
