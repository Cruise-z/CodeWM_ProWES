# pyCodeObfuscator/core/parser.py
from __future__ import annotations

import libcst as cst

def parse_code(source: str) -> cst.Module:
    """
    Parse Python source code into a LibCST.Module.
    """
    return cst.parse_module(source)


def code_from_module(module: cst.Module) -> str:
    """
    Convert a LibCST.Module back into source code.
    """
    return module.code
