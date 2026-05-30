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

# ===========================================================================
# ewdLP.py
# Description: Minimal wrapper for EWD:
# - Reuse original EWDUtils / EWDLogitsProcessor (no behavior change)
# - Remove dependency on EWDConfig by using a thin _ConfigShim
# - Cache full input_ids during generation
# - Provide zero-arg detect_last() that computes entropy via the cached model
#   and runs the original score_sequence() to get the z-score & decision.
# ===========================================================================
from __future__ import annotations
from typing import Any, Dict, List, Optional

import torch
from torch import Tensor
import time as _time
# Adjust the import path to your project layout if needed
from .ewd import EWDUtils, EWDLogitsProcessor


class _ConfigShim:
    """
    A minimal config facade that provides the attributes EWDUtils/EWDLogitsProcessor
    expect from EWDConfig, without depending on the full TransformersConfig wrapper.

    Pass these once at registration time (e.g., from regWM.py):
      - tokenizer     : HF tokenizer used during generation (a.k.a. generation_tokenizer)
      - model         : HF CausalLM model used during generation (a.k.a. generation_model)
      - device        : torch.device or str
      - vocab_size    : tokenizer.vocab_size (int)
      - gamma, delta, hash_key, z_threshold, prefix_length : algorithm params
      - gen_kwargs    : optional dict (kept for interface parity; not used here)
    """
    def __init__(
        self,
        *,
        tokenizer,
        model,
        device,
        vocab_size: int,
        gamma: float,
        delta: float,
        hash_key: int,
        z_threshold: float,
        prefix_length: int,
        gen_kwargs: Optional[Dict[str, Any]] = None,
    ):
        # Names/attributes kept aligned with ewd.py’s EWDConfig usage
        self.generation_tokenizer = tokenizer
        self.generation_model = model
        self.device = device
        self.vocab_size = int(vocab_size)
        self.gen_kwargs = {} if gen_kwargs is None else gen_kwargs

        self.gamma = float(gamma)
        self.delta = float(delta)
        self.hash_key = int(hash_key)
        self.z_threshold = float(z_threshold)
        self.prefix_length = int(prefix_length)


class EWDWMLogitsProcessor(EWDLogitsProcessor):
    """
    Wrapper that keeps the original logits biasing intact and adds:
      - runtime caching of per-row full input_ids during generation
      - zero-argument detect_last() that:
          * computes the entropy via the cached model (utils.calculate_entropy)
          * runs the original utils.score_sequence to get z-score
          * returns {"is_watermarked": bool|List[bool], "score": float|List[float]}
    """

    def __init__(
        self,
        *,
        tokenizer,
        model,
        device,
        vocab_size: int,
        gamma: float,
        delta: float,
        hash_key: int,
        z_threshold: float,
        prefix_length: int,
    ):
        # 1) Build a tiny config shim & reuse original utils/processor
        cfg = _ConfigShim(
            tokenizer=tokenizer,
            model=model,
            device=device,
            vocab_size=vocab_size,
            gamma=gamma,
            delta=delta,
            hash_key=hash_key,
            z_threshold=z_threshold,
            prefix_length=prefix_length,
        )
        utils = EWDUtils(cfg)
        super().__init__(config=cfg, utils=utils)

        # 2) Detection-time caches (do not affect biasing path)
        self._cache_full_ids_rows: Optional[List[Tensor]] = None
        self._prev_len_rows: Optional[List[int]] = None
        self._cache_bsz: Optional[int] = None

        # 3) Performance counters (do not affect biasing path)
        self._lp_time_s: float = 0.0
        self._lp_calls: int = 0

    # ---- Keep original biasing logic; just append caching afterwards ----
    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor) -> torch.FloatTensor:

        # Time ONLY the logits-processor path (pure watermark LP overhead)
        t0 = _time.perf_counter()
        try:
            scores_out = super().__call__(input_ids, scores)  # original behavior unchanged
        finally:
            # Must never affect generation; keep it best-effort
            try:
                self._lp_time_s += float(_time.perf_counter() - t0)
                self._lp_calls += 1
            except Exception:
                pass

        # Append: cache full input_ids per row for zero-arg detection later
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
                # Store a CPU clone to avoid holding on to GPU memory
                self._cache_full_ids_rows[i] = input_ids[i].detach().to("cpu").clone()
                self._prev_len_rows[i] = cur_len
        except Exception:
            # Cache failures must not impact generation
            pass

        return scores_out

    # ---- Zero-argument offline detection (batch-friendly) ----
    def detect_last(self) -> Dict[str, Any]:
        """
        Zero-argument detection using cached input_ids.

        To align with the original EWD detect_watermark() behavior, we:
          1) decode cached ids to text with skip_special_tokens=True
          2) re-tokenize with add_special_tokens=False
          3) compute entropy via utils.calculate_entropy(model, token_ids)
          4) compute z-score via utils.score_sequence(token_ids, entropy_list)
          5) compare z-score with config.z_threshold

        Returns:
          - single row: {"is_watermarked": bool, "score": float}
          - multi  row: {"is_watermarked": List[bool], "score": List[float]}
          - if nothing cached: {"error": "no_cached_tokens"}
        """
        if not self._cache_full_ids_rows:
            return {"error": "no_cached_tokens"}

        tok = getattr(self.config, "generation_tokenizer", None)  # type: ignore[attr-defined]
        mdl = getattr(self.config, "generation_model", None)      # type: ignore[attr-defined]
        if tok is None or mdl is None:
            return {"error": "missing_generation_components"}

        results_bool: List[bool] = []
        results_score: List[float] = []

        for ids_cpu in self._cache_full_ids_rows:
            if ids_cpu.numel() == 0:
                results_bool.append(False)
                results_score.append(float("-inf"))
                continue

            try:
                # 1) Decode cached ids to plain text (skip special tokens)
                text = tok.decode(ids_cpu.tolist(), skip_special_tokens=True)
                if not text:
                    results_bool.append(False)
                    results_score.append(float("-inf"))
                    continue

                # 2) Re-tokenize with add_special_tokens=False (same as original detect_watermark)
                enc = tok(text, return_tensors="pt", add_special_tokens=False)
                token_ids = enc["input_ids"][0]
                if token_ids.numel() == 0:
                    results_bool.append(False)
                    results_score.append(float("-inf"))
                    continue

                # 3) Move to target device
                ids = token_ids.to(self.config.device, non_blocking=True)  # type: ignore[attr-defined]

                # 4) Entropy & z-score using original utils
                entropy_list = self.utils.calculate_entropy(mdl, ids)
                z_score, _, _ = self.utils.score_sequence(ids, entropy_list)
            except Exception:
                # Match original behavior: on failure (e.g. too short), treat as no signal
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
        This is intended for server-side logging/benchmarking.
        """
        calls = int(self._lp_calls)
        total_s = float(self._lp_time_s)
        avg_us = (total_s / calls * 1e6) if calls > 0 else 0.0
        return {
            "lp_total_time_s": total_s,
            "lp_calls": calls,
            "lp_avg_per_call_us": float(avg_us),
        }

    def clear_cached(self) -> None:
        """Optional: manually clear caches (does not affect biasing state)."""
        self._cache_full_ids_rows = None
        self._prev_len_rows = None
        self._cache_bsz = None

    def reset_timing(self) -> None:
        """Optional: reset timing counters for a clean measurement window."""
        self._lp_time_s = 0.0
        self._lp_calls = 0
