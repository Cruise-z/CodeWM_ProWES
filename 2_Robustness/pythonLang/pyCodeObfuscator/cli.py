# cli.py
from __future__ import annotations

import pathlib
from typing import Optional

import click

from .core.rule_base import get_all_rules, RuleDirection
from .core.transformer import obfuscate_source


@click.command()
@click.argument("path", type=click.Path(exists=True, path_type=pathlib.Path))
@click.option(
    "--direction",
    type=click.Choice(["auto", "obfuscate", "normalize"]),
    default="auto",
)
def main(path: pathlib.Path, direction: str) -> None:
    """
    对单个文件或目录进行 SPT 混淆。
    """
    if direction == "auto":
        dir_enum = RuleDirection.AUTO
    elif direction == "obfuscate":
        dir_enum = RuleDirection.TO_OBFUSCATED
    else:
        dir_enum = RuleDirection.TO_NORMALIZED

    rule_types = list(get_all_rules())

    if path.is_file():
        _process_file(path, rule_types, dir_enum)
    else:
        for py_file in path.rglob("*.py"):
            _process_file(py_file, rule_types, dir_enum)


def _process_file(path: pathlib.Path, rule_types, direction: RuleDirection) -> None:
    src = path.read_text(encoding="utf8")
    new_src = obfuscate_source(src, rule_types, direction)
    path.write_text(new_src, encoding="utf8")


if __name__ == "__main__":
    main()
