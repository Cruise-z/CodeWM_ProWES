#!/usr/bin/env python3
"""LLM + local hard-rule RAG semantic-restatement attack.

Unlike the legacy file-chat script, this version performs explicit reproducible retrieval
(BM25 over an archived rule knowledge base), injects the retrieved rule cards into the
prompt, records the retrieved IDs and prompt hash, and validates syntax when tree-sitter
is available.
"""
from __future__ import annotations
import argparse
import copy
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve()
BUNDLE = HERE.parents[3] if len(HERE.parents) >= 4 else HERE.parent
for p in [BUNDLE, BUNDLE / "cStyleLang"]:
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

from rq2_revision.common import read_jsonl, write_jsonl, select_rows, stable_uid, resolve_parser_lib
from rq2_revision.rag import BM25RuleRetriever
from rq2_revision.llm_rag import rewrite_with_rag
from rq2_revision.llm_provider import OpenAICompatibleProvider, LegacyAiAPIProvider, MockIdentityProvider


def parse_args():
    ap = argparse.ArgumentParser(description="LLM + local hard-rule RAG source rewrite")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--lang", choices=["java", "cpp", "javascript"], required=True)
    ap.add_argument("--channel", choices=["id", "expr", "block", "all"], required=True)
    ap.add_argument("--source-field", default="after_watermark")
    ap.add_argument("--output-field", default="after_obfus")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--sample-size", type=int, default=None)
    ap.add_argument("--max-chars", type=int, default=1400)
    ap.add_argument("--selection", choices=["input", "longest"], default="longest")
    ap.add_argument("--top-k", type=int, default=6)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max-completion-tokens", type=int, default=None)
    ap.add_argument("--reasoning-effort", choices=["minimal", "low", "medium", "high"], default=None)
    ap.add_argument("--max-attempts", type=int, default=3)
    ap.add_argument("--retry-backoff", type=float, default=2.0)
    ap.add_argument("--request-delay", type=float, default=0.0)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--progress-every", type=int, default=25)
    ap.add_argument("--parser-lib", default=None)
    ap.add_argument("--rules", default=str(BUNDLE / "rq2_revision" / "rules" / "hard_rules.json"))

    ap.add_argument("--provider", choices=["openai-compatible", "legacy-aiapi", "mock"], default="openai-compatible")
    ap.add_argument("--base-url", default="https://api.openai.com/v1")
    ap.add_argument("--model", default="gpt-4o-mini")
    ap.add_argument("--api-key-env", default="OPENAI_API_KEY")
    ap.add_argument("--legacy-config", default=None)
    ap.add_argument("--legacy-profile", default="paid")
    ap.add_argument("--legacy-model-attr", default="gpt4")
    return ap.parse_args()


def provider_from_args(a):
    if a.provider == "mock":
        return MockIdentityProvider()
    if a.provider == "legacy-aiapi":
        if not a.legacy_config:
            raise ValueError("--legacy-config is required for --provider legacy-aiapi")
        return LegacyAiAPIProvider(a.legacy_config, a.legacy_profile, a.legacy_model_attr)
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
    retriever = BM25RuleRetriever.from_json(a.rules)
    provider = provider_from_args(a)
    rows = read_jsonl(a.input)
    selected = select_rows(rows, a.source_field, a.sample_size, a.max_chars, a.selection)

    output_path = Path(a.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out = read_jsonl(output_path) if a.resume and output_path.exists() else []
    if len(out) > len(selected):
        raise ValueError("resume output contains more rows than the selected input")
    for idx, prior in enumerate(out):
        src = selected[idx][a.source_field]
        expected_uid = selected[idx].get("_attack_uid", stable_uid(idx, src))
        if prior.get("_attack_uid") != expected_uid:
            raise ValueError(f"resume UID mismatch at row {idx}")

    mode = "a" if out else "w"
    with output_path.open(mode, encoding="utf-8") as output_handle:
        for idx in range(len(out), len(selected)):
            row = selected[idx]
            item = copy.deepcopy(row)
            src = item[a.source_field]
            item["_attack_uid"] = item.get("_attack_uid", stable_uid(idx, src))
            last_error = None
            for attempt in range(1, a.max_attempts + 1):
                try:
                    code, meta = rewrite_with_rag(
                        src, a.lang, a.channel, a.seed, item["_attack_uid"], provider, retriever,
                        parser_lib=parser_lib, temperature=a.temperature, top_k=a.top_k,
                        max_completion_tokens=a.max_completion_tokens,
                        reasoning_effort=a.reasoning_effort,
                    )
                    item[a.output_field] = code
                    meta["provider"] = a.provider
                    meta["model"] = a.model if a.provider == "openai-compatible" else a.legacy_model_attr
                    meta["attempts"] = attempt
                    if not meta.get("syntax_valid", True):
                        status = "syntax_invalid"
                    elif not meta.get("changed"):
                        status = "no_op"
                    else:
                        status = "valid_attack"
                    meta["status"] = status
                    meta["execution_status"] = "not_evaluated_non_executable_dataset"
                    item["attack_meta"] = meta
                    last_error = None
                    break
                except Exception as exc:
                    last_error = exc
                    if attempt < a.max_attempts:
                        time.sleep(a.retry_backoff * (2 ** (attempt - 1)))
            if last_error is not None:
                item[a.output_field] = ""
                item["attack_meta"] = {
                    "attack_family": "llm_rule_rag", "channel": a.channel, "language": a.lang,
                    "global_seed": a.seed, "status": "error", "syntax_valid": False,
                    "changed": False, "attempts": a.max_attempts,
                    "error": f"{type(last_error).__name__}: {last_error}",
                }
                response_meta = getattr(provider, "last_response_meta", None)
                if response_meta:
                    item["attack_meta"]["provider_response"] = response_meta
            out.append(item)
            output_handle.write(json.dumps(item, ensure_ascii=False) + "\n")
            output_handle.flush()
            if a.progress_every and (idx + 1) % a.progress_every == 0:
                print(f"progress={idx + 1}/{len(selected)} output={a.output}", flush=True)
            if a.request_delay and idx + 1 < len(selected):
                time.sleep(a.request_delay)

    n = len(out)
    changed = sum(bool(x.get("attack_meta", {}).get("changed")) for x in out)
    valid = sum(bool(x.get("attack_meta", {}).get("syntax_valid")) for x in out)
    print(f"wrote={n} changed={changed} syntax_valid={valid} output={a.output}")


if __name__ == "__main__":
    main()
