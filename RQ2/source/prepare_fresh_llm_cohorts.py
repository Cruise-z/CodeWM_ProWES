#!/usr/bin/env python3
"""Build paired, method-independent cohorts for the fresh RQ2 LLM attack.

The two methods must be evaluated on the same underlying programs.  Selecting the
longest ``after_watermark`` values independently can produce different cohorts, so
this script ranks pairs by their shared original source and assigns the same stable
UID to both rows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from rq2_revision.rule_attack import _build_parser, tree_sitter_syntax_valid


METHODS = ("srcmarker", "codemark")
DATASETS = ("github_c_funcs", "github_java_funcs", "csn_js", "csn_java")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-dir", default="outputs/fresh/base")
    parser.add_argument("--output-dir", default="outputs/fresh/llm_input")
    parser.add_argument("--sample-size", type=int, default=1000)
    parser.add_argument("--max-chars", type=int, default=1400)
    parser.add_argument("--parser-lib", default="training/SrcMarker_fresh/parser/languages.so")
    return parser.parse_args()


def read_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def sha256_text(value: str):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def original_source(row):
    for field in ("original_string", "code", "output_original_func"):
        value = row.get(field)
        if isinstance(value, str) and value:
            return value
    raise ValueError("row has no non-empty original source field")


def main():
    args = parse_args()
    if args.sample_size <= 0:
        raise ValueError("--sample-size must be positive")
    if args.max_chars <= 0:
        raise ValueError("--max-chars must be positive")

    base_dir = Path(args.base_dir)
    output_dir = Path(args.output_dir)
    manifest = {
        "selection": "shared original-source length descending, then input index",
        "eligibility": "both method after_watermark values are non-empty, <= max_chars, and baseline-syntax-valid",
        "sample_size_cap": args.sample_size,
        "max_chars": args.max_chars,
        "datasets": {},
    }

    language_for_dataset = {
        "github_c_funcs": "cpp",
        "github_java_funcs": "java",
        "csn_js": "javascript",
        "csn_java": "java",
    }
    parsers = {
        language: _build_parser(language, args.parser_lib)
        for language in sorted(set(language_for_dataset.values()))
    }

    for dataset in DATASETS:
        method_rows = {
            method: read_jsonl(base_dir / f"{method}_{dataset}.jsonl")
            for method in METHODS
        }
        row_counts = {method: len(rows) for method, rows in method_rows.items()}
        if len(set(row_counts.values())) != 1:
            raise ValueError(f"{dataset}: method row counts differ: {row_counts}")

        eligible = []
        rejected_empty = 0
        rejected_length = 0
        rejected_syntax = 0
        language = language_for_dataset[dataset]
        syntax_parser = parsers[language]
        for index, (srcmarker_row, codemark_row) in enumerate(
            zip(method_rows["srcmarker"], method_rows["codemark"])
        ):
            srcmarker_original = original_source(srcmarker_row)
            codemark_original = original_source(codemark_row)
            if srcmarker_original != codemark_original:
                raise ValueError(f"{dataset}: original source mismatch at row {index}")
            sources = (
                srcmarker_row.get("after_watermark"),
                codemark_row.get("after_watermark"),
            )
            if not all(isinstance(source, str) and source for source in sources):
                rejected_empty += 1
                continue
            if any(len(source) > args.max_chars for source in sources):
                rejected_length += 1
                continue
            if not all(
                tree_sitter_syntax_valid(syntax_parser, source, language)
                for source in sources
            ):
                rejected_syntax += 1
                continue
            eligible.append((index, srcmarker_original))

        eligible.sort(key=lambda item: (-len(item[1]), item[0]))
        selected = eligible[: args.sample_size]
        selected_indices = [index for index, _ in selected]
        selected_uids = []
        output_paths = {}

        for rank, (index, original) in enumerate(selected):
            selected_uids.append(
                f"rq2-llm-{dataset}-{index:08d}-{sha256_text(original)[:12]}"
            )

        for method in METHODS:
            cohort_rows = []
            for rank, (index, original) in enumerate(selected):
                row = dict(method_rows[method][index])
                row["_attack_uid"] = selected_uids[rank]
                row["_cohort_dataset"] = dataset
                row["_cohort_rank"] = rank
                row["_cohort_input_index"] = index
                row["_cohort_original_sha256"] = sha256_text(original)
                cohort_rows.append(row)
            output_path = output_dir / f"{method}_{dataset}.jsonl"
            write_jsonl(output_path, cohort_rows)
            output_paths[method] = {
                "path": str(output_path),
                "sha256": sha256_file(output_path),
            }

        manifest["datasets"][dataset] = {
            "input_rows": row_counts["srcmarker"],
            "shared_eligible_rows": len(eligible),
            "rejected_empty_rows": rejected_empty,
            "rejected_length_rows": rejected_length,
            "rejected_baseline_syntax_rows": rejected_syntax,
            "selected_rows": len(selected),
            "selected_input_indices_sha256": sha256_text(
                json.dumps(selected_indices, separators=(",", ":"))
            ),
            "selected_uids_sha256": sha256_text("\n".join(selected_uids)),
            "outputs": output_paths,
        }

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "cohort_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    print(f"wrote manifest: {manifest_path}")


if __name__ == "__main__":
    main()
