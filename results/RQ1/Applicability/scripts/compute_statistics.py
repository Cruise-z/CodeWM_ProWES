#!/usr/bin/env python3
import argparse
import csv
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median


OUTCOMES = ("Pass", "BE", "TE", "RE")
RNG_SEED_RE = re.compile(r"(?:^|_)rngS=([^_]+)")


def percentile(values, fraction):
    if not values:
        return ""
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def rounded(value):
    if value == "":
        return ""
    return round(value, 6)


def run_key(row):
    return row["project"], row["language"], row["seed_group"], row["method_config"]


def rng_seed(row):
    match = RNG_SEED_RE.search(row["method_config"])
    return match.group(1) if match else ""


def summarize(group_fields, rows):
    values = {field: rows[0][field] for field in group_fields}
    counts = Counter(row["category"] for row in rows)
    evaluated = [row for row in rows if row["category"] in OUTCOMES]
    pass_strengths = [float(row["strength"]) for row in evaluated if row["category"] == "Pass"]
    runs = defaultdict(list)
    for row in evaluated:
        runs[run_key(row)].append(row)
    run_pass_rates = []
    run_mean_pass_strengths = []
    for run_rows in runs.values():
        passed = [row for row in run_rows if row["category"] == "Pass"]
        run_pass_rates.append(len(passed) / len(run_rows))
        if passed:
            run_mean_pass_strengths.append(mean(float(row["strength"]) for row in passed))
    first_quartile = percentile(pass_strengths, 0.25)
    third_quartile = percentile(pass_strengths, 0.75)
    return {
        **values,
        "response_points": len(rows),
        "evaluated_points": len(evaluated),
        "parameter_runs": len({run_key(row) for row in rows}),
        **{category: counts[category] for category in OUTCOMES},
        "Excluded": counts["Excluded"],
        "point_pooled_pass_rate": rounded(counts["Pass"] / len(evaluated) if evaluated else ""),
        "pass_strength_mean": rounded(mean(pass_strengths) if pass_strengths else ""),
        "pass_strength_median": rounded(median(pass_strengths) if pass_strengths else ""),
        "pass_strength_q1": rounded(first_quartile),
        "pass_strength_q3": rounded(third_quartile),
        "pass_strength_iqr": rounded(third_quartile - first_quartile if pass_strengths else ""),
        "run_balanced_pass_rate": rounded(mean(run_pass_rates) if run_pass_rates else ""),
        "run_balanced_mean_pass_strength": rounded(
            mean(run_mean_pass_strengths) if run_mean_pass_strengths else ""
        ),
        "runs_with_pass": len(run_mean_pass_strengths),
    }


def grouped_summary(rows, group_fields):
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[field] for field in group_fields)].append(row)
    return [summarize(group_fields, group_rows) for _, group_rows in sorted(groups.items())]


def parameter_run_summary(rows):
    fields = ("watermark_method", "project", "language", "seed_group", "method_config")
    output = grouped_summary(rows, fields)
    for item in output:
        match = RNG_SEED_RE.search(item["method_config"])
        item["rng_seed"] = match.group(1) if match else ""
    ordered_fields = [*fields[:-1], "rng_seed", fields[-1]]
    return [
        {field: item[field] for field in ordered_fields}
        | {field: value for field, value in item.items() if field not in ordered_fields}
        for item in output
    ]


def seed_inventory(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["project"], row["language"])].append(row)
    output = []
    for (project, language), group_rows in sorted(groups.items()):
        seeds = sorted({rng_seed(row) for row in group_rows if rng_seed(row)}, key=lambda value: int(value))
        output.append({
            "project": project,
            "language": language,
            "rng_seeds": ",".join(seeds),
            "seed_count": len(seeds),
            "watermark_methods": ",".join(sorted({row["watermark_method"] for row in group_rows})),
            "response_points": len(group_rows),
        })
    return output


def provenance_summary(rows):
    counts = Counter(row["classification_source"] for row in rows)
    return [
        {"classification_source": source, "points": count}
        for source, count in sorted(counts.items())
    ]


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"No rows available for {path.name}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        strength = float(row["strength"])
        if not math.isfinite(strength):
            raise ValueError(f"Non-finite strength in {row['method_config']}")
    return rows


def main():
    package_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Compute derived tables from the master watermark table.")
    parser.add_argument("--input", type=Path, default=package_root / "data" / "watermark_points.csv")
    parser.add_argument("--output", type=Path, default=Path.cwd() / "derived")
    args = parser.parse_args()

    rows = read_rows(args.input.resolve())
    output = args.output.resolve()
    tables = {
        "summary_method_project_language.csv": grouped_summary(
            rows, ("watermark_method", "project", "language")
        ),
        "summary_method_project.csv": grouped_summary(rows, ("watermark_method", "project")),
        "summary_method.csv": grouped_summary(rows, ("watermark_method",)),
        "summary_parameter_runs.csv": parameter_run_summary(rows),
        "seed_inventory.csv": seed_inventory(rows),
        "classification_provenance.csv": provenance_summary(rows),
    }
    for filename, table_rows in tables.items():
        write_csv(output / filename, table_rows)
    print(f"Wrote {len(tables)} derived tables to {output}.")


if __name__ == "__main__":
    main()
