# wllmLP.py
# Fold detection logic into a method-based version of WatermarkLogitsProcessor
# Notes:
# - Do not modify the original file; keep fully compatible embedding logic through inheritance
# - Integrate WLLM's Detector into the logits processor as offline zero-argument detection
# - Automatically cache the required side-channel data (prefix_len, full_ids) at runtime for Detector checks

from __future__ import annotations
from math import sqrt
from typing import Dict, Optional, List

import torch
import time as _time
from torch import Tensor
import scipy.stats

# Reuse the base implementation from your project
from .watermark import WatermarkBase, WatermarkLogitsProcessor


class WLLMLogitsProcessor(WatermarkLogitsProcessor):
    """
    While strictly preserving the original watermark embedding / biasing call path,
    this class integrates Detector logic into the processor in an **offline zero-argument** form:
      - Automatically cache prefix_len / full_ids at runtime (batch=1 case)
      - Provide detect_last(): no need for the server to pass through ids/entropy and similar data
      - Keep z/p computation and hypothesis testing fully aligned with WatermarkDetector
    """

    def __init__(
        self,
        *args,
        tokenizer=None,                 # Optional, only for extensibility; current zero-arg detection does not depend on it
        z_threshold: float = 4.0,
        ignore_repeated_bigrams: bool = False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        # ---- Detection-time configuration (does not affect embedding logic) ----
        self._tokenizer = tokenizer
        self._z_threshold = float(z_threshold)
        self._ignore_repeated_bigrams = bool(ignore_repeated_bigrams)
        if getattr(self, "rng", None) is None:
            self.rng = torch.Generator()

        # ---- Runtime cache (used for zero-argument detection) ----
        self._cache_prev_len: Optional[int] = None
        self._cache_prefix_len: Optional[int] = None
        self._cache_full_ids: Optional[torch.LongTensor] = None

        # ---- Performance counters (pure logits-processor overhead, accumulated per __call__) ----
        self._lp_time_s: float = 0.0
        self._lp_calls: int = 0

        # simple_1 seeding requires at least one token as prefix
        self._min_prefix_len: int = 1 if getattr(self, "seeding_scheme", "simple_1") == "simple_1" else 1

    # -------------- Keep the original embedding logic intact, only append cache updates at the end --------------
    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor) -> torch.FloatTensor:
        # Time ONLY the logits-processor path (pure watermark LP overhead)
        t0 = _time.perf_counter()
        try:
            # Directly reuse the upstream WatermarkLogitsProcessor.__call__()
            # This guarantees the embedding logic stays exactly aligned with the original implementation, without handwritten drift
            scores_out = super().__call__(input_ids, scores)
        finally:
            # Best-effort timing: must never affect generation behavior
            try:
                self._lp_time_s += float(_time.perf_counter() - t0)
                self._lp_calls += 1
            except Exception:
                pass

        # ---- Runtime cache for zero-argument detection (batch=1 only; can be extended to list-based multi-batch if needed) ----
        try:
            bsz, cur_len = int(input_ids.shape[0]), int(input_ids.shape[1])
            if bsz == 1:
                if self._cache_prev_len is None or cur_len <= self._cache_prev_len:
                    # Treat this as the start of a new generation round: current length becomes prefix_len
                    self._cache_prefix_len = cur_len
                self._cache_prev_len = cur_len
                # Save the full sequence (copy to CPU to avoid GPU memory usage and lifetime issues)
                self._cache_full_ids = input_ids[0].detach().to("cpu").clone()
        except Exception:
            # Cache failures must not affect the main generation flow
            pass

        return scores

    def timing(self) -> Dict[str, float]:
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

    # ---------------------- Offline detection implementation below ----------------------
    @staticmethod
    def _compute_z_score(green_count: int, T: int, gamma: float) -> float:
        expected = gamma
        numer = green_count - expected * T
        denom = sqrt(max(1e-12, T * expected * (1 - expected)))
        return float(numer / denom)

    @staticmethod
    def _compute_p_value(z: float) -> float:
        return float(scipy.stats.norm.sf(z))

    def _score_sequence(
        self,
        input_ids: Tensor,
        prefix_len: int,
        return_num_tokens_scored: bool = True,
        return_num_green_tokens: bool = True,
        return_green_fraction: bool = True,
        return_green_token_mask: bool = False,
        return_z_score: bool = True,
        return_p_value: bool = True,
    ) -> Dict:
        """
        Aligned with WatermarkDetector._score_sequence:
          - Iterate over prefix_len..len(ids)-1 and use _get_greenlist_ids(seed_ids) at each step to determine hits
          - Count G and T, then compute z/p
        """
        score_dict: Dict = {}
        if self._ignore_repeated_bigrams:
            raise NotImplementedError("ignore_repeated_bigrams=True is not implemented yet (consistent with the official implementation)")

        prefix_len = max(self._min_prefix_len, int(prefix_len))
        num_tokens_scored = int(len(input_ids) - prefix_len)
        if num_tokens_scored < 1:
            score_dict["invalid"] = True
            return score_dict

        green_token_count, green_token_mask = 0, []
        for idx in range(prefix_len, len(input_ids)):
            curr_token = int(input_ids[idx])
            greenlist_ids = self._get_greenlist_ids(input_ids[:idx])
            if curr_token in set(int(t) for t in greenlist_ids):
                green_token_count += 1
                green_token_mask.append(True)
            else:
                green_token_mask.append(False)

        if return_num_tokens_scored:
            score_dict["num_tokens_scored"] = int(num_tokens_scored)
        if return_num_green_tokens:
            score_dict["num_green_tokens"] = int(green_token_count)
        if return_green_fraction:
            score_dict["green_fraction"] = float(green_token_count / num_tokens_scored)
        if return_z_score:
            score_dict["z_score"] = self._compute_z_score(
                green_token_count, num_tokens_scored, float(self.gamma)
            )
        if return_p_value:
            z = score_dict.get("z_score")
            if z is None:
                z = self._compute_z_score(green_token_count, num_tokens_scored, float(self.gamma))
            score_dict["p_value"] = self._compute_p_value(float(z))
        if return_green_token_mask:
            score_dict["green_token_mask"] = green_token_mask

        return score_dict

    def detect_last(self) -> Dict:
        """
        Offline zero-argument detection based on the automatically cached full_ids/prefix_len gathered during generation.
        By default, it returns scores and a decision using the initialized self._z_threshold.
        """
        if self._cache_full_ids is None or self._cache_prefix_len is None:
            raise RuntimeError("No cached sequence for detection. Run generate() with this processor first.")

        full_ids = self._cache_full_ids
        pre_len = int(self._cache_prefix_len)

        out: Dict = {}
        # 1) Score the sequence (aligned with WatermarkDetector._score_sequence)
        score_dict = self._score_sequence(input_ids=full_ids, prefix_len=pre_len)
        out.update(score_dict)
        # If the text is too short, return invalid directly
        if out.pop("invalid", False):
            self._last_detection = {"invalid": True}
            # Clear the trace cache once to avoid accidental reuse in the next round
            self._cache_full_ids = None
            self._cache_prefix_len = None
            self._cache_prev_len = None
            return {"invalid": True}
        # 2) Run the hypothesis test and fill in z/p if needed
        if "z_score" not in out:
            T = int(out.get("num_tokens_scored", 0))
            G = int(out.get("num_green_tokens", 0))
            z = self._compute_z_score(G, T, float(self.gamma))
            out["z_score"] = float(z)
            out["p_value"] = self._compute_p_value(float(z))
        thr = float(self._z_threshold)
        out["prediction"] = bool(float(out["z_score"]) > thr)
        if out["prediction"]:
            out["confidence"] = float(1.0 - float(out.get("p_value", 1.0)))
        # 3) Record the latest result and clear the trace cache
        self._last_detection = dict(out)
        self._cache_full_ids = None
        self._cache_prefix_len = None
        self._cache_prev_len = None
        return out
