# Copyright 2025 CodeWM_AutoTest.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# ==============================================================================
# stoneLP.py
# Description: Minimal wrapper: reuse original STONEUtils / STONELogitsProcessor
# - No dependency on STONEConfig (we use a thin _ConfigShim)
# - Keep original logits biasing logic untouched (super().__call__())
# - Cache full input_ids during generation and provide zero-arg detect_last()
# ==============================================================================
from __future__ import annotations
from typing import Any, Dict, List, Optional

import torch
from ..timing import (
    detection_state_enabled,
    processor_timing_enabled,
    synchronized_perf_counter,
)
from torch import Tensor

# stone.py is colocated with this wrapper.
from .stone import STONEUtils, STONELogitsProcessor


class _ConfigShim:
    """
    Minimal replacement for STONEConfig containing only attributes required
    by STONEUtils and STONELogitsProcessor. regWM.py supplies all parameters.
    """
    def __init__(
        self,
        *,
        tokenizer,              # generation_tokenizer
        vocab_size: int,
        device,                 # torch.device or str
        gamma: float,
        delta: float,
        hash_key: int,
        z_threshold: float,
        prefix_length: int,
        language: str,
        # Retained for API compatibility; this wrapper does not use them.
        model: Optional[Any] = None,
        gen_kwargs: Optional[Dict[str, Any]] = None,
    ):
        # Keep field names expected by stone.py.
        self.generation_tokenizer = tokenizer
        self.vocab_size = int(vocab_size)
        self.device = device
        self.gen_kwargs = {} if gen_kwargs is None else gen_kwargs

        self.gamma = float(gamma)
        self.delta = float(delta)
        self.hash_key = int(hash_key)
        self.z_threshold = float(z_threshold)
        self.prefix_length = int(prefix_length)
        self.language = str(language)

        # Placeholder; the upstream biasing path does not require a model.
        self.model = model


class STONEWMLogitsProcessor(STONELogitsProcessor):
    """
    Reuse upstream STONELogitsProcessor biasing and add only a configuration
    shim, per-row full-ID caching, and zero-argument detection through the
    upstream STONEUtils.score_sequence implementation.
    """

    def __init__(
        self,
        *,
        tokenizer,
        vocab_size: int,
        device,
        gamma: float,
        delta: float,
        hash_key: int,
        z_threshold: float,
        prefix_length: int,
        language: str,
        watermark_on_pl: str = "True",
        skipping_rule: Optional[str] = None,
        detector_scope: str = "generation_conditioned",
    ):
        # 1) Construct the lightweight configuration shim.
        cfg = _ConfigShim(
            tokenizer=tokenizer,
            vocab_size=vocab_size,
            device=device,
            gamma=gamma,
            delta=delta,
            hash_key=hash_key,
            z_threshold=z_threshold,
            prefix_length=prefix_length,
            language=language,
        )
        utils = STONEUtils(
            cfg,
            skipping_rule=skipping_rule,
            watermark_on_pl=watermark_on_pl,
            language=language,
        )
        # 2) Invoke the upstream constructor unchanged.
        super().__init__(
            config=cfg,
            utils=utils,
            skipping_rule=skipping_rule,
            watermark_on_pl=watermark_on_pl,
            language=language,
        )
        if detector_scope not in ("generation_conditioned", "continuation"):
            raise ValueError(
                "STONE detector_scope must be 'generation_conditioned' or 'continuation'"
            )
        self._detector_scope = detector_scope

        # 3) Add a detection cache without altering biasing.
        self._cache_full_ids_rows: Optional[List[Tensor]] = None
        self._cache_prefix_len_rows: Optional[List[int]] = None
        self._prev_len_rows: Optional[List[int]] = None
        self._cache_bsz: Optional[int] = None

        # 4) Performance counters (pure logits-processor overhead, accumulated per __call__)
        self._lp_time_s: float = 0.0
        self._lp_calls: int = 0

    # Preserve upstream biasing and append caching only.
    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor) -> torch.FloatTensor:

        timing_enabled = processor_timing_enabled()
        t0 = synchronized_perf_counter(scores) if timing_enabled else 0.0
        try:
            scores_out = super().__call__(input_ids, scores)
        finally:
            if timing_enabled:
                try:
                    self._lp_time_s += float(synchronized_perf_counter(scores) - t0)
                    self._lp_calls += 1
                except Exception:
                    pass

        # Cache each row's complete input IDs for zero-argument detection.
        if detection_state_enabled():
            try:
                bsz, cur_len = int(input_ids.shape[0]), int(input_ids.shape[1])
                need_reset = (
                    self._cache_full_ids_rows is None
                    or self._prev_len_rows is None
                    or self._cache_bsz is None
                    or self._cache_bsz != bsz
                    or any(cur_len <= pl for pl in (self._prev_len_rows or []))
                )
                if need_reset:
                    self._cache_full_ids_rows = [torch.empty(0, dtype=input_ids.dtype) for _ in range(bsz)]
                    self._cache_prefix_len_rows = [cur_len] * bsz
                    self._prev_len_rows = [0] * bsz
                    self._cache_bsz = bsz

                for i in range(bsz):
                    self._cache_full_ids_rows[i] = input_ids[i].detach().to("cpu").clone()
                    self._prev_len_rows[i] = cur_len
            except Exception:
                pass  # Cache failures must not affect generation.

        return scores_out

    # Offline detection: decode, re-tokenize without special tokens, then score.
    def detect_last(self) -> Dict[str, Any]:
        """
        Detect from full input IDs cached during generation. As in the upstream
        implementation, decode to text, re-tokenize with special tokens
        disabled, and score the resulting IDs. Return scalar fields for one
        row and lists for multiple rows.
        """
        if not self._cache_full_ids_rows:
            return {"error": "no_cached_tokens"}

        results_bool: List[bool] = []
        results_score: List[float] = []
        results_input_tokens: List[int] = []
        results_scored_tokens: List[int] = []

        prefix_lengths = self._cache_prefix_len_rows or [0] * len(self._cache_full_ids_rows)
        for ids_cpu, generation_prefix_len in zip(
            self._cache_full_ids_rows,
            prefix_lengths,
        ):
            detector_ids = (
                ids_cpu[int(generation_prefix_len):]
                if self._detector_scope == "continuation"
                else ids_cpu
            )
            results_input_tokens.append(int(detector_ids.numel()))
            results_scored_tokens.append(
                max(0, int(detector_ids.numel()) - int(self.config.prefix_length))
            )
            if detector_ids.numel() == 0:
                results_bool.append(False)
                results_score.append(float("-inf"))
                continue

            try:
                # 1) Decode plain text while skipping special tokens.
                tok = getattr(self.config, "generation_tokenizer", None)  # type: ignore[attr-defined]
                if tok is None:
                    raise RuntimeError("no_tokenizer")
                text = tok.decode(detector_ids.tolist(), skip_special_tokens=True)
                if not text:
                    # Empty text cannot be detected.
                    results_bool.append(False)
                    results_score.append(float("-inf"))
                    continue

                # 2) Re-tokenize with special tokens disabled.
                enc = tok(text, return_tensors="pt", add_special_tokens=False)
                new_ids_cpu = enc["input_ids"][0]
                if new_ids_cpu.numel() == 0:
                    results_bool.append(False)
                    results_score.append(float("-inf"))
                    continue

                ids = new_ids_cpu.to(self.config.device, non_blocking=True)  # type: ignore[attr-defined]

                # 3) Score; STONEUtils returns (z, flags, weights).
                z_score, _, _ = self.utils.score_sequence(ids)
            except Exception:
                # Match upstream behavior by returning -inf on scoring errors.
                z_score = float("-inf")

            thr = float(self.config.z_threshold)  # type: ignore[attr-defined]
            results_bool.append(bool(z_score > thr))
            results_score.append(float(z_score))

        if len(results_bool) == 1:
            return {
                "is_watermarked": results_bool[0],
                "score": results_score[0],
                "detector_scope": self._detector_scope,
                "detector_input_tokens": results_input_tokens[0],
                "num_tokens_scored": results_scored_tokens[0],
            }
        return {
            "is_watermarked": results_bool,
            "score": results_score,
            "detector_scope": self._detector_scope,
            "detector_input_tokens": results_input_tokens,
            "num_tokens_scored": results_scored_tokens,
        }

    def timing(self) -> Dict[str, Any]:
        """
        Return accumulated logits-processor runtime.
        Intended for server-side logging/benchmarking.
        """
        calls = int(self._lp_calls)
        total_s = float(self._lp_time_s)
        avg_us = (total_s / calls * 1e6) if calls > 0 else 0.0
        return {
            "lp_total_time_s": total_s,
            "lp_calls": calls,
            "lp_avg_per_call_us": float(avg_us),
        }

    def reset_timing(self) -> None:
        """Optional: reset timing counters for a clean measurement window."""
        self._lp_time_s = 0.0
        self._lp_calls = 0

    def clear_cached(self) -> None:
        """Clear the detection cache without changing biasing state."""
        self._cache_full_ids_rows = None
        self._cache_prefix_len_rows = None
        self._prev_len_rows = None
        self._cache_bsz = None


def build_codewm(resources, params):
    """Construct the STONE wrapper from declared host and vocab resources."""
    return STONEWMLogitsProcessor(
        tokenizer=resources.tokenizer,
        vocab_size=resources.component().vocab_size,
        device=resources.device,
        gamma=float(params.get("gamma", 0.5)),
        delta=float(params.get("delta", 2.0)),
        hash_key=int(params.get("hash_key", 15485863)),
        z_threshold=float(params.get("z_threshold", 4.0)),
        prefix_length=int(params.get("prefix_length", 1)),
        language=str(params.get("language", "java")),
        watermark_on_pl=str(params.get("watermark_on_pl", "False")),
        skipping_rule=params.get("skipping_rule", "all_pl"),
        detector_scope=str(params.get("detector_scope", "generation_conditioned")),
    )


def finalize_codewm_generation_evidence(processor, continuation_rows):
    """Append the sampled final token to each detector cache row."""
    cached_rows = processor._cache_full_ids_rows
    if not cached_rows or len(cached_rows) != len(continuation_rows):
        return
    for index, continuation in enumerate(continuation_rows):
        if not continuation:
            continue
        complete_continuation = torch.tensor(
            [int(token) for token in continuation],
            dtype=cached_rows[index].dtype,
        )
        if (
            cached_rows[index].numel() >= complete_continuation.numel()
            and torch.equal(
                cached_rows[index][-complete_continuation.numel():],
                complete_continuation,
            )
        ):
            continue
        cached_rows[index] = torch.cat(
            (
                cached_rows[index],
                torch.tensor([int(continuation[-1])], dtype=cached_rows[index].dtype),
            ),
            dim=0,
        )
        if processor._prev_len_rows is not None:
            processor._prev_len_rows[index] = int(cached_rows[index].numel())
