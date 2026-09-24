"""Standalone detector-state reconstruction for non-intrusive timing.

Generation-time processors deliberately avoid retaining detection-only state
when the v2 timing protocol is active.  This module initializes a fresh
processor from the final generated text immediately before ``detect_last``.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

import torch


def prepare_standalone_detector(processor: Any) -> None:
    """Perform lazy, method-owned initialization outside the timed region."""

    ensure = getattr(processor, "_ensure_watermarker", None)
    if callable(ensure):
        ensure()


def _load_token_ids(processor: Any, token_ids: torch.LongTensor) -> None:
    """Populate only the state consumed by the released ``detect_last`` API."""

    method = str(getattr(processor, "_codewm_method", "")).lower()
    ids = token_ids.detach().to("cpu", dtype=torch.long).flatten().clone()
    token_count = int(ids.numel())

    if method in {"wllm", "sweet"}:
        processor._cache_full_ids = ids
        processor._cache_prefix_len = 0
        processor._cache_prev_len = token_count
        if method == "sweet":
            processor._cache_entropy = []
        return

    if method in {"ewd", "stone"}:
        processor._cache_full_ids_rows = [ids]
        processor._cache_prefix_len_rows = [0]
        processor._prev_len_rows = [token_count]
        processor._cache_bsz = 1
        return

    if method == "codeip":
        mode = str(getattr(processor, "_mode", "")).lower()
        if mode != "random":
            raise ValueError(
                "standalone CodeIP extraction currently supports mode='random' only"
            )
        processor._cache_full_ids = ids
        processor._cache_prefix_len = 0
        processor._cache_prev_len = token_count
        processor._finalized_continuation_length = token_count
        return

    if method == "waterfall":
        row = [int(token) for token in ids.tolist()]
        cache_limit = getattr(processor, "_cache_limit", None)
        if cache_limit is not None and len(row) > int(cache_limit):
            row = row[-int(cache_limit):]
        processor._cache_rows_ids = [row]
        processor._prev_seen_len_rows = [token_count]
        return

    raise ValueError(f"standalone detection is not implemented for method {method!r}")


def detect_text(
    processor: Any,
    tokenizer: Any,
    text: str,
) -> Tuple[Dict[str, Any], int]:
    """Tokenize final text, reconstruct detector state, and run detection.

    The caller owns the CUDA synchronization and wall-clock boundary.  Thus
    tokenization, CPU/GPU transfer inside a method, and detector execution are
    all included in the reported extraction latency.
    """

    encoded = tokenizer(text, return_tensors="pt", add_special_tokens=False)
    token_ids = encoded["input_ids"][0]
    input_tokens = int(token_ids.numel())
    if input_tokens <= 0:
        raise ValueError("standalone detection requires non-empty generated text")
    _load_token_ids(processor, token_ids)
    result = processor.detect_last()
    if not isinstance(result, dict):
        raise TypeError("detect_last() must return a dictionary")
    return result, input_tokens
