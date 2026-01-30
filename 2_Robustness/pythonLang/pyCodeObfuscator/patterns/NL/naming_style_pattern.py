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
    words: List[str]  # 统一用小写单词序列表示，比如 ["user", "add", "num"]


_PY_KEYWORDS = set(keyword.kwlist)
_PY_CONSTANTS = {"True", "False", "None"}


def _is_valid_identifier(name: str) -> bool:
    # 简单过滤：合法标识符、不是关键字、不是 True/False/None
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

    # 统一用小写单词
    return [p.lower() for p in parts]


def _split_camel(name: str) -> Optional[List[str]]:
    """
    UserAddNum  （这里按你的例子，首字母大写的 Camel / Pascal）
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
      - 第一段：全小写
      - 后续每段：首字母大写，其余小写
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
    只对 cst.Name 做命名风格匹配。
    返回风格 + 单词序列；若不是这三种风格之一，则返回 None。
    """
    name = name_node.value

    if not _is_valid_identifier(name):
        return None

    # 优先判断 snake，再判断 user_Add_Num，再判断 UserAddNum
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
    根据统一小写单词序列构造不同风格的标识符字符串。
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

    # 理论上不会走到这里
    return "_".join(words)
