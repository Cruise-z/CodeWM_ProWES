# LLM + hard-rule RAG prompt used by RQ2

The runtime prompt is assembled from two archived templates plus the retrieved rule cards.

## System prompt

```text
You are performing a source-to-source robustness transformation for a code-watermark experiment.

Your goal is to weaken source-level watermark carriers while preserving the program's externally observable behavior as much as possible.

STRICT REQUIREMENTS:
1. Preserve the function signature, return type, parameters, exceptions/throws contract, and externally visible API.
2. Do not delete required computation, add new I/O, add logging, add network/file access, or intentionally make the program fail.
3. Apply only transformations justified by the retrieved RULE CARDS below. If a rule's preconditions are not clearly satisfied, skip that rule.
4. Do not invent library methods, types, identifiers, imports, or APIs that are not already available in the source.
5. Preserve variable binding and scope. Avoid identifier collisions and reserved keywords.
6. Preserve evaluation order and side effects. In particular, do not duplicate or remove side-effecting expressions.
7. Keep the output in the same programming language as the input.
8. Prefer multiple safe rewrites within the requested channel when feasible, but semantic preservation has priority over attack strength.
9. Return no explanation outside the required output format.

OUTPUT FORMAT:
<applied_rules>comma-separated RULE_ID values actually used, or NONE</applied_rules>
```{language}
<transformed source code only>
```
```

## User prompt template

```text
REQUESTED_LANGUAGE: {language}
REQUESTED_CHANNEL: {channel}
RANDOMIZATION_SEED: {seed}

RETRIEVED RULE CARDS:
{rule_cards}

SOURCE CODE:
```{language}
{source_code}
```

Rewrite the source code using only safe, applicable retrieved rules from the requested channel. If no retrieved rule can be applied safely, return the original source unchanged and use <applied_rules>NONE</applied_rules>.
```

## Retrieval protocol

- Knowledge base: `pipeline/rules/hard_rules.json`.
- Retriever: deterministic local BM25 (`pipeline/rag.py`).
- Filter: language-compatible rules; for Id/Expr/Block attacks, also filter to the requested channel.
- ALL: retrieve a channel-diverse set, forcing at least one candidate from Id, Expr, and Block when available.
- Default `top_k`: 6.
- The exact retrieved rule IDs and SHA-256 of the final prompt are stored in `attack_meta` for every generated sample.

This is the final reproducible local rule-RAG protocol used by the experiment.
