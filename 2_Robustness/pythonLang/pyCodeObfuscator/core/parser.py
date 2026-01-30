# pyCodeObfuscator/core/parser.py
from __future__ import annotations

import libcst as cst

def parse_code(source: str) -> cst.Module:
    """
    把 Python 源码解析成 LibCST.Module。
    """
    return cst.parse_module(source)


def code_from_module(module: cst.Module) -> str:
    """
    把 LibCST.Module 格式化回源码字符串。
    """
    return module.code
