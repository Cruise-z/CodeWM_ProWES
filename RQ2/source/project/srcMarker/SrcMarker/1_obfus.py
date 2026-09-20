#!/usr/bin/env python3
"""Final reproducible rule-based RQ2 attack driver.

This script is intended to be copied into the SrcMarker repository together with the
``pipeline`` and ``cStyleCodeObfuscator`` packages.
"""
from __future__ import annotations
import argparse
import copy
import sys
from pathlib import Path

# Make the Artifact source tree importable when run in-place.
HERE = Path(__file__).resolve()
BUNDLE = HERE.parents[3] if len(HERE.parents) >= 4 else HERE.parent
for p in [BUNDLE, BUNDLE / "cStyleLang"]:
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

from pipeline.common import read_jsonl, write_jsonl, select_rows, stable_uid, resolve_parser_lib
from pipeline.rule_attack import attack_code


def parse_args():
    ap = argparse.ArgumentParser(description="Channel-stratified semantics-preserving rule attack")
    ap.add_argument("--input", required=True, help="Watermarked JSONL input")
    ap.add_argument("--output", required=True, help="Attacked JSONL output")
    ap.add_argument("--lang", choices=["java", "cpp", "javascript"], required=True)
    ap.add_argument("--channel", choices=["id", "expr", "block", "all"], required=True)
    ap.add_argument("--source-field", default="after_watermark")
    ap.add_argument("--output-field", default="after_obfus")
    ap.add_argument("--seed", type=int, default=42, help="Global attack seed")
    ap.add_argument("--parser-lib", default=None)
    ap.add_argument("--sample-size", type=int, default=None)
    ap.add_argument("--max-chars", type=int, default=None)
    ap.add_argument("--selection", choices=["input", "longest"], default="input")
    return ap.parse_args()


def main():
    a = parse_args()
    parser_lib = resolve_parser_lib(a.parser_lib, str(BUNDLE))
    rows = read_jsonl(a.input)
    selected = select_rows(rows, a.source_field, a.sample_size, a.max_chars, a.selection)

    out = []
    for idx, row in enumerate(selected):
        item = copy.deepcopy(row)
        src = item[a.source_field]
        uid = stable_uid(idx, src)
        item["_attack_uid"] = item.get("_attack_uid", uid)
        try:
            attacked, meta = attack_code(
                src, a.lang, a.channel, a.seed, item["_attack_uid"], parser_lib,
                safe_mode=True,
            )
            item[a.output_field] = attacked
            item["attack_meta"] = meta
            if not meta["syntax_valid"]:
                status = "syntax_invalid"
            elif not meta["changed"]:
                status = "no_op"
            else:
                status = "valid_attack"
            item["attack_meta"]["status"] = status
            item["attack_meta"]["execution_status"] = "not_evaluated_non_executable_dataset"
        except Exception as e:
            item[a.output_field] = ""
            item["attack_meta"] = {
                "attack_family": "rule", "channel": a.channel, "language": a.lang,
                "global_seed": a.seed, "status": "error",
                "error": f"{type(e).__name__}: {e}", "syntax_valid": False, "changed": False,
            }
        out.append(item)

    write_jsonl(a.output, out)
    n = len(out)
    changed = sum(bool(x.get("attack_meta", {}).get("changed")) for x in out)
    valid = sum(bool(x.get("attack_meta", {}).get("syntax_valid")) for x in out)
    print(f"wrote={n} changed={changed} syntax_valid={valid} output={a.output}")


if __name__ == "__main__":
    main()
