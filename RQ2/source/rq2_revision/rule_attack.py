from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional, Tuple

from .common import derive_seed, sha256_text


@dataclass
class OperatorRecord:
    transformer: str
    key: str
    status: str
    changed: bool = False
    syntax_valid: Optional[bool] = None
    error: Optional[str] = None


def _build_parser(lang: str, parser_lib: str):
    import tree_sitter
    parser = tree_sitter.Parser()
    language = tree_sitter.Language(parser_lib, lang)
    parser.set_language(language)
    return parser


def _wrap_for_parse(code: str, lang: str) -> str:
    if lang == "java":
        return f"public class RQ2Wrapper {{\n{code}\n}}"
    return code


def tree_sitter_syntax_valid(parser, code: str, lang: str) -> bool:
    tree = parser.parse(_wrap_for_parse(code, lang).encode("utf-8"))
    return not bool(getattr(tree.root_node, "has_error", False))


def build_transformers(lang: str, channel: str, seed: int, safe_mode: bool = True):
    import cStyleCodeObfuscator.mutable_tree.transformers as T
    # Give each stochastic operator an independent deterministic sub-seed.
    def s(offset: int) -> int:
        return (seed + 0x9E3779B9 * offset) & 0xFFFFFFFF

    id_ops = [
        T.IdRenameTransformer(seed=s(1)),
        T.VarNameStyleTransformer(seed=s(2)),
    ]
    expr_ops = [
        T.UpdateTransformer(seed=s(3), safe_only=safe_mode),
        T.LoopCondTransformer(seed=s(4), lang=lang),
        T.DefaultParamTransformer(lang=lang),
        T.EquivalentFormsTransformer(lang=lang),
    ]
    block_ops = [
        T.ReposVarDeclTransformer(seed=s(5), lang=lang),
        T.LoopStmtTransformer(),
        T.IfFlatNestTransformer(),
        T.ConditionTransformer(),
        T.CondBlockSwapTransformer(),
    ]
    mapping = {"id": id_ops, "expr": expr_ops, "block": block_ops,
               "all": id_ops + expr_ops + block_ops}
    if channel not in mapping:
        raise ValueError(f"Unknown channel {channel}; choose id|expr|block|all")
    return mapping[channel]


def attack_code(source: str, lang: str, channel: str, global_seed: int,
                sample_key: str, parser_lib: str, safe_mode: bool = True) -> Tuple[str, Dict[str, Any]]:
    from cStyleCodeObfuscator.code_transform_provider import CodeTransformProvider
    from cStyleCodeObfuscator.format import preprocess_code

    sample_seed = derive_seed(global_seed, sample_key, channel)
    parser = _build_parser(lang, parser_lib)
    transformers = build_transformers(lang, channel, sample_seed, safe_mode=safe_mode)
    provider = CodeTransformProvider(lang, parser, transformers)

    current = preprocess_code(source)
    original = current
    records: List[OperatorRecord] = []

    # Every operator is attempted once on the current code.  A candidate is accepted
    # only if it changes the source and remains syntactically valid both to tree-sitter
    # and to the MutableAST adaptor.  There is deliberately no theoretical-key fallback.
    for transformer in transformers:
        for key in transformer.get_available_transforms():
            rec = OperatorRecord(transformer=transformer.name, key=key, status="attempted")
            try:
                candidate = provider.code_transform(current, [key])
                rec.changed = candidate != current
                if not rec.changed:
                    rec.status = "inapplicable_or_noop"
                    records.append(rec)
                    continue
                syntax_ok = tree_sitter_syntax_valid(parser, candidate, lang)
                if syntax_ok:
                    try:
                        provider.to_mutable_tree(candidate)
                    except Exception:
                        syntax_ok = False
                rec.syntax_valid = syntax_ok
                if not syntax_ok:
                    rec.status = "rejected_syntax"
                    records.append(rec)
                    continue
                current = candidate
                rec.status = "applied"
            except Exception as e:
                rec.status = "error"
                rec.error = f"{type(e).__name__}: {e}"
            records.append(rec)

    final_syntax = tree_sitter_syntax_valid(parser, current, lang)
    try:
        provider.to_mutable_tree(current)
        final_mutable = True
    except Exception:
        final_mutable = False
    final_syntax = bool(final_syntax and final_mutable)

    meta = {
        "attack_family": "rule",
        "channel": channel,
        "language": lang,
        "safe_mode": safe_mode,
        "global_seed": global_seed,
        "sample_seed": sample_seed,
        "source_sha256": sha256_text(source),
        "changed": current != original,
        "syntax_valid": final_syntax,
        "operators": [asdict(r) for r in records],
        "applied_keys": [r.key for r in records if r.status == "applied"],
    }
    return current, meta
