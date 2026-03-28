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
import time as _time
from torch import Tensor

# Adjust the import path according to your project layout:
# assume stone.py is in the same directory as this file
from .stone import STONEUtils, STONELogitsProcessor


class _ConfigShim:
    """
    Provide only the attributes required by STONEUtils / STONELogitsProcessor
    to replace STONEConfig; parameters are passed in during construction from regWM.py.
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
        # The following two are only kept for interface compatibility; this wrapper does not use generation_model/gen_kwargs
        model: Optional[Any] = None,
        gen_kwargs: Optional[Dict[str, Any]] = None,
    ):
        # Keep field names consistent with those used in stone.py
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

        # Placeholder only; the original biasing logic does not need model
        self.model = model


class STONEWMLogitsProcessor(STONELogitsProcessor):
    """
    Reuse the original STONELogitsProcessor biasing logic;
    only adds:
      - injecting parameters via _ConfigShim in __init__ (no STONEConfig dependency)
      - caching the latest full input_ids for the current round after __call__ (per row)
      - detect_last(): perform offline zero-argument detection from the cache using the original STONEUtils.score_sequence
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
    ):
        # 1) Build a lightweight "config" and reuse the original utility class / processor
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
        # 2) Call the parent constructor to preserve original behavior
        super().__init__(
            config=cfg,
            utils=utils,
            skipping_rule=skipping_rule,
            watermark_on_pl=watermark_on_pl,
            language=language,
        )

        # 3) Added only: cache for detection, without affecting bias logic
        self._cache_full_ids_rows: Optional[List[Tensor]] = None
        self._prev_len_rows: Optional[List[int]] = None
        self._cache_bsz: Optional[int] = None

        # 4) Performance counters (pure logits-processor overhead, accumulated per __call__)
        self._lp_time_s: float = 0.0
        self._lp_calls: int = 0

    # —— Keep the original bias logic unchanged: call the parent __call__, then append cache updates —— #
    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor) -> torch.FloatTensor:

        # Time ONLY the logits-processor path (pure watermark LP overhead)
        t0 = _time.perf_counter()
        try:
            scores_out = super().__call__(input_ids, scores)  # Original logic remains unchanged
        finally:
            # Best-effort timing: must never affect generation behavior
            try:
                self._lp_time_s += float(_time.perf_counter() - t0)
                self._lp_calls += 1
            except Exception:
                pass

        # Additional step: cache the full input_ids for the current round (per row) for zero-argument detection
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
                self._prev_len_rows = [0] * bsz
                self._cache_bsz = bsz

            for i in range(bsz):
                self._cache_full_ids_rows[i] = input_ids[i].detach().to("cpu").clone()
                self._prev_len_rows[i] = cur_len
        except Exception:
            pass  # Cache failures must not affect generation

        return scores_out

    # —— Offline zero-argument detection aligned with the original logic (decode -> re-tokenize without special tokens -> score) —— #
    def detect_last(self) -> Dict[str, Any]:
        """
        Perform zero-argument detection using the full input_ids cached during generation.
        To stay consistent with the source implementation, it first decodes the cached ids into text,
        then re-tokenizes with add_special_tokens=False before scoring.
        Returns:
          single row: {"is_watermarked": bool, "score": float}
          multiple rows: {"is_watermarked": List[bool], "score": List[float]}
        """
        if not self._cache_full_ids_rows:
            return {"error": "no_cached_tokens"}

        results_bool: List[bool] = []
        results_score: List[float] = []

        for ids_cpu in self._cache_full_ids_rows:
            if ids_cpu.numel() == 0:
                results_bool.append(False)
                results_score.append(float("-inf"))
                continue

            try:
                # 1) Decode into plain text (skip special tokens)
                tok = getattr(self.config, "generation_tokenizer", None)  # type: ignore[attr-defined]
                if tok is None:
                    raise RuntimeError("no_tokenizer")
                text = tok.decode(ids_cpu.tolist(), skip_special_tokens=True)
                if not text:
                    # Empty text cannot be detected: return -inf
                    results_bool.append(False)
                    results_score.append(float("-inf"))
                    continue

                # 2) Re-tokenize with add_special_tokens=False to obtain ids
                enc = tok(text, return_tensors="pt", add_special_tokens=False)
                new_ids_cpu = enc["input_ids"][0]
                if new_ids_cpu.numel() == 0:
                    results_bool.append(False)
                    results_score.append(float("-inf"))
                    continue

                ids = new_ids_cpu.to(self.config.device, non_blocking=True)  # type: ignore[attr-defined]

                # 3) Score the sequence (STONEUtils.score_sequence returns (z, flags, weights))
                z_score, _, _ = self.utils.score_sequence(ids)
            except Exception:
                # Stay aligned with the source implementation: return -inf on exceptions, such as insufficient length
                z_score = float("-inf")

            thr = float(self.config.z_threshold)  # type: ignore[attr-defined]
            results_bool.append(bool(z_score > thr))
            results_score.append(float(z_score))

        if len(results_bool) == 1:
            return {"is_watermarked": results_bool[0], "score": results_score[0]}
        return {"is_watermarked": results_bool, "score": results_score}

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
        """Optional: manually clear the cache without affecting bias state."""
        self._cache_full_ids_rows = None
        self._prev_len_rows = None
        self._cache_bsz = None
