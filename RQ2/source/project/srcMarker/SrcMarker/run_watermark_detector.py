#!/usr/bin/env python3
"""Handoff attacked JSONL to the existing SrcMarker watermark extractor and merge results.

The original ``2_eval_obfus.py`` expects ``<dataset_dir>/obfus.jsonl``.  This wrapper
preserves invalid/no-output attacks instead of silently losing them: only valid attacked
rows are staged for extraction, then ``obfus_extract`` results are merged back by a
stable ``_attack_uid``.
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def read_jsonl(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def write_jsonl(p, rows):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--attack-jsonl", required=True)
    ap.add_argument("--merged-output", required=True)
    ap.add_argument("--evaluator", default="./2_eval_obfus.py")
    ap.add_argument("--checkpoint-path", required=True)
    ap.add_argument("--lang", choices=["java", "cpp", "javascript"], required=True)
    ap.add_argument("--dataset", choices=["github_c_funcs", "github_java_funcs", "csn_java", "csn_js"], required=True)
    ap.add_argument("--n-bits", type=int, default=4)
    ap.add_argument("--model-arch", choices=["gru", "transformer"], default="gru")
    ap.add_argument("--shared-encoder", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--work-output-dir", default="./results_obfus")
    ap.add_argument("--dry-run", action="store_true")
    return ap.parse_args()


def main():
    a = parse_args()
    rows = read_jsonl(a.attack_jsonl)
    valid = []
    for i, r in enumerate(rows):
        uid = r.get("_attack_uid") or f"row-{i}"
        r["_attack_uid"] = uid
        meta = r.get("attack_meta", {})
        if meta.get("changed") is False or meta.get("status") == "no_op":
            r["detector_status"] = "skipped_no_op"
        elif r.get("after_obfus") and meta.get("syntax_valid", True):
            valid.append(r)
        else:
            r["detector_status"] = "skipped_invalid_attack"

    if a.dry_run:
        print(f"rows={len(rows)} detector_eligible={len(valid)}")
        print("evaluator=", a.evaluator)
        return

    if not valid:
        write_jsonl(a.merged_output, rows)
        print("No detector-eligible rows; wrote merged output without extraction.")
        return

    with tempfile.TemporaryDirectory(prefix="rq2_detector_") as td:
        td = Path(td)
        staged = td / "obfus.jsonl"
        write_jsonl(staged, valid)
        out_name = "rq2_detector_eval.jsonl"
        cmd = [
            os.environ.get("PYTHON", "python"), a.evaluator,
            "--checkpoint_path", a.checkpoint_path,
            "--lang", a.lang,
            "--dataset", a.dataset,
            "--dataset_dir", str(td),
            "--n_bits", str(a.n_bits),
            "--model_arch", a.model_arch,
            "--seed", str(a.seed),
            "--output_dir", a.work_output_dir,
            "--output_filename", out_name,
        ]
        if a.shared_encoder:
            cmd.append("--shared_encoder")
        subprocess.run(cmd, check=True)
        eval_path = Path(a.work_output_dir) / a.lang / out_name
        eval_rows = read_jsonl(eval_path)
        by_uid = {r.get("_attack_uid"): r for r in eval_rows if r.get("_attack_uid")}
        # Older evaluator copies raw JSON fields, so UID should survive.  Fall back to order.
        if not by_uid and len(eval_rows) == len(valid):
            by_uid = {valid[i]["_attack_uid"]: eval_rows[i] for i in range(len(valid))}

        for r in rows:
            uid = r["_attack_uid"]
            er = by_uid.get(uid)
            if er is None:
                if r.get("detector_status") is None:
                    r["detector_status"] = "missing_detector_result"
                continue
            r["obfus_extract"] = er.get("obfus_extract")
            r["detector_status"] = "ok" if er.get("obfus_extract") is not None else "missing_prediction"

    write_jsonl(a.merged_output, rows)
    print(f"merged detector results into {a.merged_output}")


if __name__ == "__main__":
    main()
