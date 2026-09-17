#!/usr/bin/env python3
import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path


PROJECTS = ("brick_breaker", "caro", "flappy_bird", "snake", "tank_battle")
CATEGORY_ORDER = ("Pass", "BE", "TE", "RE", "Excluded", "Unknown")
STRENGTH_RE = re.compile(r"_(-?\d+(?:\.\d+)?)$")
METHOD_RE = re.compile(r"_game_([^_]+)_T=")


def directories(path):
    try:
        return sorted((entry for entry in path.iterdir() if entry.is_dir()), key=lambda item: item.name)
    except FileNotFoundError:
        return []


def files(path, pattern):
    try:
        return sorted(path.glob(pattern), key=lambda item: item.name)
    except FileNotFoundError:
        return []


def method_directories(results_dir):
    for first_level in directories(results_dir):
        if first_level.name.isdigit():
            for method_dir in directories(first_level):
                yield first_level.name, method_dir
        else:
            yield "", first_level


def latest_evaluation_log(dt_results):
    logs = []
    for output_dir in directories(dt_results):
        candidate = output_dir / "evaluation.log"
        if candidate.is_file():
            logs.append(candidate)
    return max(logs, key=lambda item: item.parent.name) if logs else None


def classify_log(text):
    lower = text.lower()

    final_success_patterns = (
        "evaluation, packaging, and smoke run-check finished successfully",
        "evaluation, packaging, and smart runtime check finished successfully",
        '"phase":"runtime_check","status":"success"',
    )
    pass_patterns = (
        "100% tests passed",
        "build success",
        "test result: ok",
    )
    compilation_patterns = (
        "cmake error",
        "cmake generate step failed",
        "compilation failure",
        "compilation error",
        "failed to compile",
        "cannot find symbol",
        "syntaxerror:",
        "gmake: ***",
        "make: ***",
        "could not compile",
        "plug-in resolution exception",
        "pluginresolutionexception",
        "could not be resolved",
        "no matching distribution found",
    )
    runtime_patterns = (
        '"phase":"runtime_check","status":"runtime_error"',
        "runtime_error:",
        "runtime error",
        "segmentation fault",
        "core dumped",
        "test step timed out",
        "timeout expired",
        " killed ",
        "exception in thread",
    )
    test_error_patterns = (
        "short test summary info",
        "error tests/",
        "tests failed",
        "test failures",
        "there were test failures",
        "failures!!!",
        "test result: failed",
        "assertionerror",
        "assertion failed",
    )

    if any(pattern in lower for pattern in final_success_patterns):
        return "Pass"
    if any(pattern in lower for pattern in runtime_patterns):
        return "RE"
    if any(pattern in lower for pattern in test_error_patterns) or re.search(r"\b[1-9]\d* failed(?:,| in )", lower):
        return "TE"
    if any(pattern in lower for pattern in compilation_patterns):
        return "BE"
    if any(pattern in lower for pattern in pass_patterns) or re.search(r"(?:^|\n)\d+ passed in \d", lower):
        return "Pass"
    last_line = next((line.strip() for line in reversed(text.splitlines()) if line.strip()), "")
    if "running pytest" in lower and re.fullmatch(r"[.fFeEsSxX]+", last_line):
        return "RE"
    return "Unknown"


def calibration_score(log_category, target_category):
    if target_category == log_category:
        return 100
    if target_category == "Excluded":
        return 10 if log_category == "Unknown" else 0
    if log_category == "Unknown":
        return 5
    return 0


def hungarian_maximize(score_matrix):
    size = len(score_matrix)
    max_score = max(max(row) for row in score_matrix) if size else 0
    costs = [[max_score - value for value in row] for row in score_matrix]
    row_potential = [0] * (size + 1)
    column_potential = [0] * (size + 1)
    matching = [0] * (size + 1)
    path = [0] * (size + 1)
    for row_index in range(1, size + 1):
        matching[0] = row_index
        column = 0
        minimum = [float("inf")] * (size + 1)
        used = [False] * (size + 1)
        while True:
            used[column] = True
            matched_row = matching[column]
            delta = float("inf")
            next_column = 0
            for candidate in range(1, size + 1):
                if used[candidate]:
                    continue
                reduced = costs[matched_row - 1][candidate - 1] - row_potential[matched_row] - column_potential[candidate]
                if reduced < minimum[candidate]:
                    minimum[candidate] = reduced
                    path[candidate] = column
                if minimum[candidate] < delta:
                    delta = minimum[candidate]
                    next_column = candidate
            for candidate in range(size + 1):
                if used[candidate]:
                    row_potential[matching[candidate]] += delta
                    column_potential[candidate] -= delta
                else:
                    minimum[candidate] -= delta
            column = next_column
            if matching[column] == 0:
                break
        while True:
            previous = path[column]
            matching[column] = matching[previous]
            column = previous
            if column == 0:
                break
    assignment = [0] * size
    for column in range(1, size + 1):
        assignment[matching[column] - 1] = column - 1
    return assignment


def calibrate_rows(method_rows, expected):
    if not expected:
        for row in method_rows:
            row["category"] = "Excluded"
            row["classification_source"] = "no_batch_summary"
        return
    summary_total = sum(expected.values())
    if summary_total > len(method_rows):
        raise ValueError("Batch summary contains more results than embedded DTResults points")
    slots = []
    for category in ("Pass", "BE", "TE", "RE"):
        slots.extend([category] * expected[category])
    slots.extend(["Excluded"] * (len(method_rows) - summary_total))
    scores = [
        [calibration_score(row["log_category"], category) for category in slots]
        for row in method_rows
    ]
    assignment = hungarian_maximize(scores)
    for row, slot_index in zip(method_rows, assignment):
        row["category"] = slots[slot_index]
        if row["category"] == "Excluded":
            row["classification_source"] = "excluded_by_batch_summary"
        elif row["category"] == row["log_category"]:
            row["classification_source"] = "log_and_batch_summary"
        else:
            row["classification_source"] = "batch_summary_calibrated"


def read_summary_category(method_dir):
    summaries = files(method_dir, "*summary*.json")
    if not summaries:
        return {}
    with summaries[-1].open(encoding="utf-8") as handle:
        counts = json.load(handle).get("counts", {})
    return {
        "BE": counts.get("[Build Error]", 0) + counts.get("[Packaging Error]", 0),
        "RE": counts.get("[Runtime Error]", 0),
        "TE": counts.get("[Test Error]", 0),
        "Pass": counts.get("[Pass]", 0),
    }




def extract(workspace):
    rows = []
    validations = []
    for project in PROJECTS:
        project_dir = workspace / project
        for language_dir in directories(project_dir):
            prefix = f"{project}_"
            if not language_dir.name.startswith(prefix):
                continue
            language = language_dir.name[len(prefix):]
            for seed_group, method_dir in method_directories(language_dir / "results"):
                method_match = METHOD_RE.search(method_dir.name)
                if not method_match:
                    continue
                method = method_match.group(1)
                method_rows = []
                embedded_count = 0
                for strength_dir in directories(method_dir):
                    strength_match = STRENGTH_RE.search(strength_dir.name)
                    if not strength_match:
                        continue
                    dt_results = strength_dir / "DTResults"
                    embedded = dt_results.is_dir()
                    if not embedded:
                        continue
                    embedded_count += 1
                    log_path = latest_evaluation_log(dt_results)
                    if log_path:
                        text = log_path.read_text(encoding="utf-8", errors="replace")
                        category = classify_log(text)
                        relative_log = str(log_path.relative_to(workspace))
                    else:
                        category = "Unknown"
                        relative_log = ""
                    method_rows.append({
                        "watermark_method": method,
                        "project": project,
                        "language": language,
                        "seed_group": seed_group,
                        "method_config": method_dir.name,
                        "strength": float(strength_match.group(1)),
                        "log_category": category,
                        "category": "",
                        "classification_source": "",
                        "embedded": "yes",
                        "evaluation_log": relative_log,
                    })
                expected = read_summary_category(method_dir)
                calibrate_rows(method_rows, expected)
                rows.extend(method_rows)
                observed = Counter(row["category"] for row in method_rows)
                validations.append({
                    "project": project,
                    "language": language,
                    "seed_group": seed_group,
                    "method_config": method_dir.name,
                    "embedded_points": embedded_count,
                    **{f"observed_{key}": observed[key] for key in CATEGORY_ORDER},
                    **{f"summary_{key}": expected.get(key, "") for key in CATEGORY_ORDER[:-1]},
                })
    return rows, validations


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    package_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Rebuild the master table from raw project-level test repositories."
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        required=True,
        help="Directory containing the five raw project directories.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=package_root / "data" / "watermark_points.csv",
        help="Destination master CSV file.",
    )
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    output = args.output.resolve()
    rows, validations = extract(workspace)
    rows.sort(key=lambda row: (row["watermark_method"], row["project"], row["language"], row["method_config"], row["strength"]))

    raw_fields = list(rows[0]) if rows else [
        "watermark_method", "project", "language", "seed_group", "method_config",
        "strength", "log_category", "category", "classification_source", "embedded", "evaluation_log",
    ]
    write_csv(output, rows, raw_fields)

    methods = {row["watermark_method"] for row in rows}
    no_summary = sum(
        all(item.get(f"summary_{category}", "") == "" for category in ("Pass", "BE", "TE", "RE"))
        for item in validations
    )
    print(f"Wrote {len(rows)} embedded points across {len(methods)} methods to {output}.")
    print(f"Validated {len(validations) - no_summary} configurations against batch summaries; {no_summary} had no summary.")


if __name__ == "__main__":
    main()
