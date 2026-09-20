from __future__ import annotations
import re
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from .common import derive_seed, sha256_text
from .rag import BM25RuleRetriever

RULE_TAG_RE = re.compile(r"<applied_rules>(.*?)</applied_rules>", re.I | re.S)
FENCE_RE = re.compile(r"```(?:java|javascript|js|cpp|c\+\+|c)?\s*\n(.*?)\n```", re.I | re.S)


def load_prompt(name: str) -> str:
    return (Path(__file__).resolve().parent / "prompts" / name).read_text(encoding="utf-8")


def parse_llm_output(text: str) -> Tuple[str, list[str]]:
    rm = RULE_TAG_RE.search(text)
    rules = []
    if rm:
        raw = rm.group(1).strip()
        if raw.upper() != "NONE":
            rules = [x.strip() for x in raw.split(",") if x.strip()]
    cm = FENCE_RE.search(text)
    if not cm:
        raise ValueError("LLM response did not contain a fenced source-code block")
    return cm.group(1).strip(), rules


def build_messages(source: str, language: str, channel: str, seed: int,
                   retriever: BM25RuleRetriever, top_k: int = 6):
    query = f"{language} {channel} source-to-source watermark robustness " + source[:2500]
    rules = retriever.retrieve(query, language=language, channel=channel, top_k=top_k)
    rule_cards = "\n\n---\n\n".join(r.prompt_block() for r in rules)
    system = load_prompt("system_prompt.txt").format(language=language)
    user = load_prompt("user_prompt_template.txt").format(
        language=language, channel=channel, seed=seed,
        rule_cards=rule_cards, source_code=source,
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}], rules


def rewrite_with_rag(source: str, language: str, channel: str, global_seed: int,
                     sample_key: str, provider, retriever: BM25RuleRetriever,
                     parser_lib: Optional[str] = None, temperature: float = 0.0,
                     top_k: int = 6,
                     max_completion_tokens: Optional[int] = None,
                     reasoning_effort: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
    sample_seed = derive_seed(global_seed, sample_key, "llm-rag-" + channel)
    messages, rules = build_messages(source, language, channel, sample_seed, retriever, top_k=top_k)
    raw = provider.chat(
        messages, temperature=temperature, seed=sample_seed,
        max_completion_tokens=max_completion_tokens,
        reasoning_effort=reasoning_effort,
    )
    code, reported_rules = parse_llm_output(raw)

    syntax_valid = None
    if parser_lib:
        from .rule_attack import _build_parser, tree_sitter_syntax_valid
        parser = _build_parser(language, parser_lib)
        syntax_valid = tree_sitter_syntax_valid(parser, code, language)

    allowed = {r.id for r in rules}
    unknown_reported = [r for r in reported_rules if r not in allowed]
    meta = {
        "attack_family": "llm_rule_rag",
        "channel": channel,
        "language": language,
        "global_seed": global_seed,
        "sample_seed": sample_seed,
        "source_sha256": sha256_text(source),
        "changed": code != source,
        "syntax_valid": syntax_valid,
        "retriever": "BM25-local-hard-rules",
        "retrieved_rule_ids": [r.id for r in rules],
        "reported_applied_rule_ids": reported_rules,
        "unknown_reported_rule_ids": unknown_reported,
        "temperature": temperature,
        "max_completion_tokens": max_completion_tokens,
        "reasoning_effort": reasoning_effort,
        "prompt_sha256": sha256_text(messages[0]["content"] + "\n" + messages[1]["content"]),
    }
    response_meta = getattr(provider, "last_response_meta", None)
    if response_meta:
        meta["provider_response"] = response_meta
    return code, meta
