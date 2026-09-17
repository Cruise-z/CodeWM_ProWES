#!/usr/bin/env python3
"""
Reproduce the per-strength detectability table directly from the original logs.

No external packages are required.

Outputs:
  derived/detectability_values.csv
  derived/all_metrics_long.csv
  derived/audit_summary.json
  tables/table_per_strength_auroc.tex

Key definitions:
  Pool   = logged pooled AUROC over positive strengths {0.5,1.0,2.0,3.0}
  FNR_5  = 1 - pooled TPR@FPR=5%
  Values are displayed as percentages using ROUND_HALF_UP to 2 decimals.
"""
from pathlib import Path
import re, csv, json
from decimal import Decimal, ROUND_HALF_UP

EXPECTED_STRENGTHS = [0.5, 1.0, 2.0, 3.0]
EXPECTED_METHODS = ["wllm", "ewd", "sweet", "stone", "waterfall"]
REPO_DISPLAY = {
    "brick_breaker_game": "Brick Breaker",
    "tiny_calculator": "Calculator",
    "tiny_snake_game": "Snake Game",
    "flappy_bird_java": "Flappy Bird",
}
METHOD_DISPLAY = {
    "wllm": "WLLM",
    "ewd": "EWD",
    "sweet": "SWEET",
    "stone": "STONE",
    "waterfall": "Waterfall",
}
REPO_ORDER = ["Brick Breaker", "Calculator", "Snake Game", "Flappy Bird"]
METHOD_ORDER = ["WLLM", "EWD", "SWEET", "STONE", "Waterfall"]

OVERALL_MARKER = "==================== OVERALL METRICS (pos pooled across strengths) ===================="

def pct2(x):
    """percentage display with conventional ROUND_HALF_UP."""
    return Decimal(str(x * 100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def parse_log(path):
    text = Path(path).read_text(encoding="utf-8", errors="strict")
    blocks = text.split(OVERALL_MARKER)[1:]
    runs = []
    long_rows = []

    for block_index, block in enumerate(blocks, 1):
        m = re.search(
            r"\[AUROC\] overall pooled = ([0-9.]+) \(Npos=(\d+), Nneg=(\d+)\)",
            block,
        )
        if not m:
            raise ValueError(f"{path}: block {block_index}: missing pooled AUROC")
        pooled_auroc, overall_npos, overall_nneg = float(m.group(1)), int(m.group(2)), int(m.group(3))

        # Parse all pooled TPR/FPR lines.
        pooled_tpr = {}
        for tm in re.finditer(
            r"\[TPR@FPR=([0-9.]+)%\] TPR=([0-9.]+)\s+thr=([-+0-9.eE]+)",
            block,
        ):
            pooled_tpr[float(tm.group(1))] = {
                "tpr": float(tm.group(2)),
                "threshold": float(tm.group(3)),
            }

        # Parse per-strength AUROC and each strength's TPR/FPR lines.
        per_strength = {}
        strength_headers = list(re.finditer(
            r"\[Strength=([0-9.]+)\] AUROC=([0-9.]+)\s+\(Npos=(\d+), Nneg=(\d+)\)",
            block,
        ))
        for i, sm in enumerate(strength_headers):
            strength = float(sm.group(1))
            start = sm.end()
            end = strength_headers[i+1].start() if i+1 < len(strength_headers) else len(block)
            sb = block[start:end]
            tprs = {}
            for tm in re.finditer(
                r"TPR@FPR=([0-9.]+)%\s*:\s*TPR=([0-9.]+)\s+thr=([-+0-9.eE]+)",
                sb,
            ):
                tprs[float(tm.group(1))] = {
                    "tpr": float(tm.group(2)),
                    "threshold": float(tm.group(3)),
                }
            per_strength[strength] = {
                "auroc": float(sm.group(2)),
                "npos": int(sm.group(3)),
                "nneg": int(sm.group(4)),
                "tpr": tprs,
            }

        save_csv = re.search(r"\[INFO\] Saved CSV:\s+(.+?\.csv)", block)
        save_json = re.search(r"\[INFO\] Saved summary JSON:\s+(.+?\.json)", block)
        if not save_csv or not save_json:
            raise ValueError(f"{path}: block {block_index}: missing saved-result provenance")

        result_csv_path = save_csv.group(1).strip()
        result_json_path = save_json.group(1).strip()
        bn = Path(result_csv_path).name
        fm = re.match(
            r"det_eval_(.+)_(wllm|sweet|ewd|stone|waterfall)_(\d{8}_\d{6})\.csv$",
            bn,
        )
        if not fm:
            raise ValueError(f"Cannot infer repository/method from {bn}")
        repo, method, timestamp = fm.groups()

        run = {
            "source_log": Path(path).name,
            "block_index": block_index,
            "repository_id": repo,
            "repository": REPO_DISPLAY.get(repo, repo),
            "method_id": method,
            "method": METHOD_DISPLAY[method],
            "timestamp": timestamp,
            "saved_csv_path": result_csv_path,
            "saved_summary_json_path": result_json_path,
            "overall_auroc": pooled_auroc,
            "overall_npos": overall_npos,
            "overall_nneg": overall_nneg,
            "pooled_tpr": pooled_tpr,
            "per_strength": per_strength,
        }
        runs.append(run)

        long_rows.append({
            "source_log": Path(path).name,
            "repository": run["repository"],
            "method": run["method"],
            "scope": "pooled",
            "strength": "",
            "auroc": pooled_auroc,
            "npos": overall_npos,
            "nneg": overall_nneg,
            "fpr_percent": "",
            "tpr": "",
            "threshold": "",
        })
        for fpr, data in sorted(pooled_tpr.items()):
            long_rows.append({
                "source_log": Path(path).name,
                "repository": run["repository"],
                "method": run["method"],
                "scope": "pooled_tpr",
                "strength": "",
                "auroc": "",
                "npos": overall_npos,
                "nneg": overall_nneg,
                "fpr_percent": fpr,
                "tpr": data["tpr"],
                "threshold": data["threshold"],
            })
        for strength, data in sorted(per_strength.items()):
            long_rows.append({
                "source_log": Path(path).name,
                "repository": run["repository"],
                "method": run["method"],
                "scope": "per_strength",
                "strength": strength,
                "auroc": data["auroc"],
                "npos": data["npos"],
                "nneg": data["nneg"],
                "fpr_percent": "",
                "tpr": "",
                "threshold": "",
            })
            for fpr, td in sorted(data["tpr"].items()):
                long_rows.append({
                    "source_log": Path(path).name,
                    "repository": run["repository"],
                    "method": run["method"],
                    "scope": "per_strength_tpr",
                    "strength": strength,
                    "auroc": "",
                    "npos": data["npos"],
                    "nneg": data["nneg"],
                    "fpr_percent": fpr,
                    "tpr": td["tpr"],
                    "threshold": td["threshold"],
                })
    return runs, long_rows

def validate(runs):
    issues = []
    if len(runs) != 20:
        issues.append(f"Expected 20 repository-method runs, found {len(runs)}")

    seen = {(r["repository"], r["method"]) for r in runs}
    expected = {(repo, method) for repo in REPO_ORDER for method in METHOD_ORDER}
    if seen != expected:
        issues.append(f"Repository-method coverage mismatch. Missing={sorted(expected-seen)}, Extra={sorted(seen-expected)}")

    for r in runs:
        strengths = sorted(r["per_strength"].keys())
        if strengths != EXPECTED_STRENGTHS:
            issues.append(f'{r["repository"]}/{r["method"]}: strengths={strengths}')
        if (r["overall_npos"], r["overall_nneg"]) != (80,20):
            issues.append(f'{r["repository"]}/{r["method"]}: overall N={(r["overall_npos"],r["overall_nneg"])}')
        for s, d in r["per_strength"].items():
            if (d["npos"], d["nneg"]) != (20,20):
                issues.append(f'{r["repository"]}/{r["method"]}/strength={s}: N={(d["npos"],d["nneg"])}')

        # With equal positive counts and the same 20 negatives, pooled AUROC must equal
        # the arithmetic mean of per-strength AUROCs. The logs satisfy this identity.
        mean_strength_auroc = sum(r["per_strength"][s]["auroc"] for s in EXPECTED_STRENGTHS) / 4.0
        if abs(mean_strength_auroc - r["overall_auroc"]) > 1e-12:
            issues.append(
                f'{r["repository"]}/{r["method"]}: pooled AUROC {r["overall_auroc"]} '
                f'!= mean per-strength AUROC {mean_strength_auroc}'
            )
        if 5.0 not in r["pooled_tpr"]:
            issues.append(f'{r["repository"]}/{r["method"]}: missing pooled TPR@FPR=5%')
        for val in [r["overall_auroc"]] + [d["auroc"] for d in r["per_strength"].values()]:
            if not (0.0 <= val <= 1.0):
                issues.append(f'{r["repository"]}/{r["method"]}: invalid AUROC {val}')
        for fpr, d in r["pooled_tpr"].items():
            if not (0.0 <= d["tpr"] <= 1.0):
                issues.append(f'{r["repository"]}/{r["method"]}: invalid pooled TPR {d["tpr"]}')
    return issues

def build_value_rows(runs):
    idx = {(r["repository"], r["method"]): r for r in runs}
    rows = []
    for repo in REPO_ORDER:
        for method in METHOD_ORDER:
            r = idx[(repo, method)]
            rows.append({
                "Repository": repo,
                "Method": method,
                "AUROC_0.5": str(pct2(r["per_strength"][0.5]["auroc"])),
                "AUROC_1.0": str(pct2(r["per_strength"][1.0]["auroc"])),
                "AUROC_2.0": str(pct2(r["per_strength"][2.0]["auroc"])),
                "AUROC_3.0": str(pct2(r["per_strength"][3.0]["auroc"])),
                "Pool": str(pct2(r["overall_auroc"])),
                "FNR5": str(pct2(1.0 - r["pooled_tpr"][5.0]["tpr"])),
                "SourceLog": r["source_log"],
                "SavedCSV": r["saved_csv_path"],
                "SavedSummaryJSON": r["saved_summary_json_path"],
            })
    return rows

def latex(rows):
    by_repo = {}
    for r in rows:
        by_repo.setdefault(r["Repository"], []).append(r)
    lines = [
r"""\begin{table}[!t]
\centering
\begin{threeparttable}
\caption{Per-strength watermark detectability across representative repositories.}
\label{tab:per-strength-auroc}
\scriptsize
\setlength{\tabcolsep}{1.7pt}
\renewcommand{\arraystretch}{1.05}

\begin{tabular*}{\columnwidth}{@{\extracolsep{\fill}}lcccccc@{}}
\toprule
\textbf{Method}
& \multicolumn{4}{c}{\textbf{AUROC at $\delta$}}
& \textbf{Pool}
& \textbf{FNR$_5$} \\
\cmidrule(lr){2-5}
& .5 & 1.0 & 2.0 & 3.0 & & \\
\midrule"""
    ]
    for ri, repo in enumerate(REPO_ORDER):
        lines.append("")
        lines.append(rf"\multicolumn{{7}}{{l}}{{\textit{{{repo}}}}}\\[-1pt]")
        for r in by_repo[repo]:
            method = r["Method"]
            lines.append(
                f'{method:<9} & {float(r["AUROC_0.5"]):5.2f} & {float(r["AUROC_1.0"]):5.2f} '
                f'& {float(r["AUROC_2.0"]):5.2f} & {float(r["AUROC_3.0"]):5.2f} '
                f'& {float(r["Pool"]):5.2f} & {float(r["FNR5"]):5.2f} \\\\'
            )
        if ri < len(REPO_ORDER)-1:
            lines.append(r"\midrule")
    lines.extend([
r"""\bottomrule
\end{tabular*}

\begin{tablenotes}[flushleft]
\footnotesize
\item \textbf{Notation:}
(1) Each per-strength AUROC compares watermarked outputs at the indicated
strength with the corresponding $\delta=0$ outputs.
(2) Pool denotes AUROC obtained by pooling the four positive strengths
$\delta\in\{0.5,1.0,2.0,3.0\}$.
(3) $\mathrm{FNR}_{5}=1-\mathrm{TPR@FPR{=}5\%}$.
(4) All values are percentages. CodeIP is omitted because it does not
provide a continuous detector score.
\end{tablenotes}

\end{threeparttable}
\end{table}
"""])
    return "\n".join(lines)

def main():
    root = Path(__file__).resolve().parents[1]
    log_dir = root / "raw_logs"
    derived_dir = root / "derived"
    table_dir = root / "tables"
    derived_dir.mkdir(exist_ok=True)
    table_dir.mkdir(exist_ok=True)

    runs, long_rows = [], []
    for p in sorted(log_dir.glob("*.txt")):
        rs, ls = parse_log(p)
        runs.extend(rs); long_rows.extend(ls)

    issues = validate(runs)
    rows = build_value_rows(runs)

    with (derived_dir/"detectability_values.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    with (derived_dir/"all_metrics_long.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(long_rows[0].keys()))
        w.writeheader(); w.writerows(long_rows)

    audit = {
        "status": "PASS" if not issues else "FAIL",
        "issues": issues,
        "n_runs": len(runs),
        "repositories": REPO_ORDER,
        "methods": METHOD_ORDER,
        "strengths": EXPECTED_STRENGTHS,
        "expected_per_strength_npos": 20,
        "expected_per_strength_nneg": 20,
        "expected_pooled_npos": 80,
        "expected_pooled_nneg": 20,
        "table_definition": {
            "Pool": "logged pooled AUROC across strengths 0.5,1.0,2.0,3.0",
            "FNR5": "1 - pooled TPR@FPR=5%",
            "display": "percentage, ROUND_HALF_UP, 2 decimals"
        },
        "statistical_note": (
            "With Nneg=20, empirical FPR resolution is 5 percentage points. "
            "Therefore the table's FNR5 is directly supported, while FPR targets below 5% "
            "are intrinsically coarse and are not used in the requested LaTeX table."
        )
    }
    (derived_dir/"audit_summary.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    (table_dir/"table_per_strength_auroc.tex").write_text(latex(rows), encoding="utf-8")

    print(json.dumps(audit, indent=2))
    if issues:
        raise SystemExit(2)

if __name__ == "__main__":
    main()
