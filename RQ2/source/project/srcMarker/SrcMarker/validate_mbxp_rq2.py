#!/usr/bin/env python3
"""Execution-based transformation-validity check on MBXP/MXEval JSONL.

The script baseline-qualifies canonical MBXP programs with their official tests, applies
the same RQ2 source transformation to the canonical function, reinserts the transformed
function into the original program, and reruns the tests.  It reports both transformation
coverage and EPR among changed, syntactically valid attacks.
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve()
BUNDLE = HERE.parents[3] if len(HERE.parents) >= 4 else HERE.parent
for p in [BUNDLE, BUNDLE / "cStyleLang"]:
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

from pipeline.common import read_jsonl, stable_uid, resolve_parser_lib, sha256_text
from pipeline.rule_attack import attack_code
from pipeline.rag import BM25RuleRetriever
from pipeline.llm_rag import rewrite_with_rag
from pipeline.llm_provider import OpenAICompatibleProvider, MockIdentityProvider


def run(cmd, cwd=None, timeout=20, env=None):
    try:
        cp = subprocess.run(cmd, cwd=cwd, timeout=timeout, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, env=env)
        return cp.returncode == 0, cp.stdout[-4000:], cp.stderr[-4000:]
    except Exception as e:
        return False, "", f"{type(e).__name__}: {e}"


def execute_program(program: str, lang: str, work: Path, timeout: int, *,
                    cpp_bin: str = "g++", javac_bin: str = "javac",
                    java_bin: str = "java", node_bin: str = "node"):
    if lang == "cpp":
        src = work / "main.cpp"; exe = work / "main.out"; src.write_text(program, encoding="utf-8")
        ok, so, se = run([cpp_bin, str(src), "-O0", "-std=c++17", "-o", str(exe)], timeout=timeout)
        if not ok: return False, "compile", se
        ok, so, se = run([str(exe)], timeout=timeout)
        return ok, "pass" if ok else "test", se or so
    if lang == "java":
        src = work / "Main.java"; src.write_text(program, encoding="utf-8")
        ok, so, se = run([javac_bin, str(src)], cwd=str(work), timeout=timeout)
        if not ok: return False, "compile", se
        ok, so, se = run([java_bin, "-cp", str(work), "Main"], cwd=str(work), timeout=timeout)
        return ok, "pass" if ok else "test", se or so
    if lang == "javascript":
        src = work / "main.js"; src.write_text(program, encoding="utf-8")
        env = os.environ.copy()
        shim_root = str(BUNDLE / "pipeline" / "node_shims")
        env["NODE_PATH"] = shim_root + (os.pathsep + env["NODE_PATH"] if env.get("NODE_PATH") else "")
        ok, so, se = run([node_bin, str(src)], cwd=str(work), timeout=timeout, env=env)
        return ok, "pass" if ok else "test", se or so
    raise ValueError(lang)


def function_from_sample(sample, lang):
    if sample.get("original_string") is not None:
        return sample["original_string"]
    prompt = sample["prompt"]
    sol = sample["canonical_solution"]
    signature = prompt.rstrip().split("\n")[-1]
    if lang == "java":
        lines = sol.strip().split("\n")
        body_without_class_close = "\n".join(lines[:-1]) if lines and lines[-1].strip() == "}" else sol
        return signature + "\n" + body_without_class_close
    return signature + "\n" + sol


def compose_program(sample):
    if sample.get("original_string") is not None:
        prompt = sample["prompt"]
        signature = prompt.rstrip().split("\n")[-1]
        signature_pos = prompt.rfind(signature)
        if signature_pos < 0:
            raise ValueError("Could not locate function signature in MBXP prompt")
        prefix = prompt[:signature_pos]
        suffix = "\n}\n" if "class " in prefix and sample["original_string"].rstrip().endswith("}") else "\n"
        return prefix + sample["original_string"].rstrip() + suffix + sample["test"]
    return sample["prompt"] + sample["canonical_solution"] + sample["test"]


def reinsert_function(sample, original_function, transformed_function):
    program = compose_program(sample)
    if original_function not in program:
        # Be tolerant to one newline-normalization difference.
        compact_original = original_function.rstrip()
        idx = program.find(compact_original)
        if idx < 0:
            raise ValueError("Could not locate canonical function inside MBXP program")
        return program[:idx] + transformed_function + program[idx + len(compact_original):]
    return program.replace(original_function, transformed_function, 1)


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, help="MBXP/MXEval JSONL with prompt/canonical_solution/test/task_id")
    ap.add_argument("--lang", choices=["java", "cpp", "javascript"], required=True)
    ap.add_argument("--channel", choices=["id", "expr", "block", "all"], required=True)
    ap.add_argument("--attack", choices=["rule", "llm-rag"], default="rule")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--parser-lib", default=None)
    ap.add_argument("--output", required=True)
    ap.add_argument("--summary", required=True)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--rules", default=str(BUNDLE / "pipeline" / "rules" / "hard_rules.json"))
    ap.add_argument("--provider", choices=["openai-compatible", "mock"], default="mock")
    ap.add_argument("--base-url", default="https://api.openai.com/v1")
    ap.add_argument("--model", default="gpt-4o-mini")
    ap.add_argument("--api-key-env", default="OPENAI_API_KEY")
    ap.add_argument("--top-k", type=int, default=6)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max-completion-tokens", type=int, default=None)
    ap.add_argument("--reasoning-effort", choices=["minimal", "low", "medium", "high"], default=None)
    ap.add_argument("--max-attempts", type=int, default=3)
    ap.add_argument("--retry-backoff", type=float, default=2.0)
    ap.add_argument("--request-delay", type=float, default=0.0)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--progress-every", type=int, default=25)
    ap.add_argument("--cpp-bin", default="g++")
    ap.add_argument("--javac-bin", default="javac")
    ap.add_argument("--java-bin", default="java")
    ap.add_argument("--node-bin", default="node")
    return ap.parse_args()


def make_provider(a):
    if a.provider == "mock": return MockIdentityProvider()
    return OpenAICompatibleProvider(a.base_url, a.model, a.api_key_env)


def main():
    a = parse_args()
    if a.max_attempts <= 0:
        raise ValueError("--max-attempts must be positive")
    if a.max_completion_tokens is not None and a.max_completion_tokens <= 0:
        raise ValueError("--max-completion-tokens must be positive")
    if a.retry_backoff < 0 or a.request_delay < 0:
        raise ValueError("retry and request delays must be non-negative")
    parser_lib = resolve_parser_lib(a.parser_lib, str(BUNDLE))
    all_rows = read_jsonl(a.dataset)
    if a.offset < 0:
        raise ValueError("--offset must be non-negative")
    indexed_rows = list(enumerate(all_rows))[a.offset:]
    if a.limit is not None:
        indexed_rows = indexed_rows[:a.limit]
    indexed_rows = [
        (idx, sample) for idx, sample in indexed_rows
        if sample.get("canonical_solution") is not None or sample.get("original_string") is not None
    ]
    retriever = BM25RuleRetriever.from_json(a.rules) if a.attack == "llm-rag" else None
    provider = make_provider(a) if a.attack == "llm-rag" else None

    output_path = Path(a.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results = read_jsonl(output_path) if a.resume and output_path.exists() else []
    if len(results) > len(indexed_rows):
        raise ValueError("resume output contains more rows than the selected input")
    for position, prior in enumerate(results):
        idx, sample = indexed_rows[position]
        expected_task_id = str(sample.get("task_id", idx))
        if prior.get("task_id") != expected_task_id:
            raise ValueError(f"resume task_id mismatch at row {position}")

    output_mode = "a" if results else "w"
    output_handle = output_path.open(output_mode, encoding="utf-8")

    def emit(record):
        results.append(record)
        output_handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        output_handle.flush()
        if a.progress_every and len(results) % a.progress_every == 0:
            print(f"progress={len(results)}/{len(indexed_rows)} output={a.output}", flush=True)

    for idx, sample in indexed_rows[len(results):]:
        task_id = str(sample.get("task_id", idx))
        uid = stable_uid(idx, task_id)
        rec = {"task_id": task_id, "attack": a.attack, "channel": a.channel}
        baseline_program = compose_program(sample)
        with tempfile.TemporaryDirectory(prefix="rq2_mbxp_base_") as td:
            ok, stage, log = execute_program(
                baseline_program, a.lang, Path(td), a.timeout,
                cpp_bin=a.cpp_bin, javac_bin=a.javac_bin,
                java_bin=a.java_bin, node_bin=a.node_bin,
            )
        rec["baseline_pass"] = bool(ok); rec["baseline_stage"] = stage
        if not ok:
            rec["baseline_log"] = log
            rec["status"] = "baseline_fail"
            emit(rec)
            continue

        function = function_from_sample(sample, a.lang)
        rec["original_function_sha256"] = sha256_text(function)
        try:
            if a.attack == "rule":
                transformed, meta = attack_code(function, a.lang, a.channel, a.seed, uid, parser_lib)
            else:
                last_error = None
                for attempt in range(1, a.max_attempts + 1):
                    try:
                        transformed, meta = rewrite_with_rag(
                            function, a.lang, a.channel, a.seed, uid,
                            provider, retriever, parser_lib=parser_lib,
                            temperature=a.temperature, top_k=a.top_k,
                            max_completion_tokens=a.max_completion_tokens,
                            reasoning_effort=a.reasoning_effort,
                        )
                        meta["attempts"] = attempt
                        last_error = None
                        break
                    except Exception as exc:
                        last_error = exc
                        if attempt < a.max_attempts:
                            time.sleep(a.retry_backoff * (2 ** (attempt - 1)))
                if last_error is not None:
                    raise last_error
            meta["provider"] = a.provider if a.attack == "llm-rag" else None
            meta["model"] = a.model if a.attack == "llm-rag" else None
            rec["attack_meta"] = meta
            rec["after_obfus"] = transformed
            rec["transformed_function_sha256"] = sha256_text(transformed)
            rec["changed"] = bool(meta.get("changed"))
            rec["syntax_valid"] = bool(meta.get("syntax_valid", True))
            if not rec["changed"]:
                rec["status"] = "no_op"
                emit(rec)
                if a.attack == "llm-rag" and a.request_delay:
                    time.sleep(a.request_delay)
                continue
            if not rec["syntax_valid"]:
                rec["status"] = "syntax_invalid"
                emit(rec)
                if a.attack == "llm-rag" and a.request_delay:
                    time.sleep(a.request_delay)
                continue
            attacked_program = reinsert_function(sample, function, transformed)
            with tempfile.TemporaryDirectory(prefix="rq2_mbxp_attack_") as td:
                ok2, stage2, log2 = execute_program(
                    attacked_program, a.lang, Path(td), a.timeout,
                    cpp_bin=a.cpp_bin, javac_bin=a.javac_bin,
                    java_bin=a.java_bin, node_bin=a.node_bin,
                )
            rec["post_pass"] = bool(ok2); rec["post_stage"] = stage2
            if not ok2:
                rec["post_log"] = log2
            rec["status"] = "valid_attack" if ok2 else "execution_invalid"
        except Exception as e:
            rec["status"] = "error"; rec["error"] = f"{type(e).__name__}: {e}"
            response_meta = getattr(provider, "last_response_meta", None) if provider else None
            if response_meta:
                rec["provider_response"] = response_meta
        emit(rec)
        if a.attack == "llm-rag" and a.request_delay:
            time.sleep(a.request_delay)

    output_handle.close()
    baseline = [r for r in results if r.get("baseline_pass")]
    changed = [r for r in baseline if r.get("changed")]
    valid = [r for r in changed if r.get("syntax_valid")]
    passed = [r for r in valid if r.get("post_pass")]
    summary = {
        "n_total": len(results), "n_baseline_pass": len(baseline),
        "n_changed": len(changed), "n_syntax_valid_changed": len(valid), "n_post_pass": len(passed),
        "attack_coverage": len(changed)/len(baseline) if baseline else None,
        "syntax_validity_given_changed": len(valid)/len(changed) if changed else None,
        "EPR_given_valid_changed": len(passed)/len(valid) if valid else None,
        "language": a.lang, "channel": a.channel, "attack": a.attack, "seed": a.seed,
        "provider": a.provider if a.attack == "llm-rag" else None,
        "model": a.model if a.attack == "llm-rag" else None,
        "status_counts": {
            status: sum(r.get("status") == status for r in results)
            for status in ["baseline_fail", "no_op", "syntax_invalid", "execution_invalid", "valid_attack", "error"]
        },
    }
    Path(a.summary).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
