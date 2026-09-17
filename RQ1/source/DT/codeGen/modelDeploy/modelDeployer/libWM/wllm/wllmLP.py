# wllmLP.py
# Integrate detection into the WatermarkLogitsProcessor implementation.
# Notes:
# - Preserve the upstream embedding logic through inheritance.
# - Expose the WLLM detector as an offline, zero-argument method.
# - Cache the required side information (prefix_len and full_ids) at runtime.

from __future__ import annotations
from math import sqrt
from typing import Dict, Optional, List

import torch
from torch import Tensor
import scipy.stats

from ..timing import synchronized_perf_counter

# Reuse the upstream implementation.
from .watermark import WatermarkBase, WatermarkLogitsProcessor


class WLLMLogitsProcessor(WatermarkLogitsProcessor):
    """
    Preserve the watermark embedding/biasing behavior while integrating the
    detector as an offline zero-argument method:
      - cache prefix_len and full_ids at runtime for batch size one;
      - expose detect_last() without requiring server-provided side data;
      - retain WatermarkDetector-compatible z/p calculations and testing.
    """

    def __init__(
        self,
        *args,
        tokenizer=None,                 # Optional extension; not needed here.
        z_threshold: float = 4.0,
        ignore_repeated_bigrams: bool = False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        # Detection configuration; it does not alter embedding.
        self._tokenizer = tokenizer
        self._z_threshold = float(z_threshold)
        self._ignore_repeated_bigrams = bool(ignore_repeated_bigrams)
        if getattr(self, "rng", None) is None:
            self.rng = torch.Generator()

        # Runtime cache for zero-argument detection.
        self._cache_prev_len: Optional[int] = None
        self._cache_prefix_len: Optional[int] = None
        self._cache_full_ids: Optional[torch.LongTensor] = None

        # ---- Performance counters (pure logits-processor overhead, accumulated per __call__) ----
        self._lp_time_s: float = 0.0
        self._lp_calls: int = 0

        # simple_1 seeding requires at least one prefix token.
        self._min_prefix_len: int = 1 if getattr(self, "seeding_scheme", "simple_1") == "simple_1" else 1

    # Preserve upstream embedding and append caching only.
    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor) -> torch.FloatTensor:
        # Time ONLY the logits-processor path (pure watermark LP overhead)
        t0 = synchronized_perf_counter(scores)
        try:
            # Delegate directly to the upstream embedding implementation.
            scores_out = super().__call__(input_ids, scores)
        finally:
            # Best-effort timing: must never affect generation behavior
            try:
                self._lp_time_s += float(synchronized_perf_counter(scores) - t0)
                self._lp_calls += 1
            except Exception:
                pass

        # Runtime cache for zero-argument detection (batch size one).
        try:
            bsz, cur_len = int(input_ids.shape[0]), int(input_ids.shape[1])
            if bsz == 1:
                if self._cache_prev_len is None or cur_len <= self._cache_prev_len:
                    # A shorter/equal sequence starts a new generation.
                    self._cache_prefix_len = cur_len
                self._cache_prev_len = cur_len
                # Copy the full sequence to CPU to avoid GPU lifetime issues.
                self._cache_full_ids = input_ids[0].detach().to("cpu").clone()
        except Exception:
            # Cache failures must not affect generation.
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

    # Offline detection implementation.
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
        Match WatermarkDetector._score_sequence: iterate over generated tokens,
        test green-list membership, and compute G, T, z, and p.
        """
        score_dict: Dict = {}
        if self._ignore_repeated_bigrams:
            raise NotImplementedError(
                "ignore_repeated_bigrams=True is not implemented upstream"
            )

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
        Detect from the full_ids/prefix_len cached during generation. Return
        the score and decision using the configured z threshold.
        """
        if self._cache_full_ids is None or self._cache_prefix_len is None:
            raise RuntimeError("No cached sequence for detection. Run generate() with this processor first.")

        full_ids = self._cache_full_ids
        pre_len = int(self._cache_prefix_len)

        out: Dict = {}
        # 1) Score using WatermarkDetector-compatible semantics.
        score_dict = self._score_sequence(input_ids=full_ids, prefix_len=pre_len)
        out.update(score_dict)
        # Return invalid for a sequence that is too short.
        if out.pop("invalid", False):
            self._last_detection = {"invalid": True}
            # Clear the trace cache before the next generation.
            self._cache_full_ids = None
            self._cache_prefix_len = None
            self._cache_prev_len = None
            return {"invalid": True}
        # 2) Run the hypothesis test and populate z/p.
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
        # 3) Save the result and clear the trace cache.
        self._last_detection = dict(out)
        self._cache_full_ids = None
        self._cache_prefix_len = None
        self._cache_prev_len = None
        return out


def build_codewm(resources, params):
    """Construct the CodeWM wrapper from declared framework resources."""
    ignore_repeated_bigrams = params.get("ignore_repeated_bigrams", False)
    if not isinstance(ignore_repeated_bigrams, bool):
        raise ValueError("WLLM ignore_repeated_bigrams must be a JSON boolean")
    if ignore_repeated_bigrams:
        raise ValueError(
            "WLLM ignore_repeated_bigrams=true is not implemented by this adapter"
        )
    return WLLMLogitsProcessor(
        vocab=resources.vocab_ids(),
        gamma=params.get("gamma", 0.5),
        delta=params.get("delta", 1),
        tokenizer=resources.tokenizer,
        z_threshold=float(params.get("z_threshold", 4.0)),
        ignore_repeated_bigrams=ignore_repeated_bigrams,
    )


def finalize_codewm_generation_evidence(processor, continuation_rows):
    """Synchronize the detector cache with the complete batch-one continuation."""
    if (
        len(continuation_rows) != 1
        or processor._cache_full_ids is None
        or processor._cache_prefix_len is None
    ):
        return
    prefix_len = int(processor._cache_prefix_len)
    prefix = processor._cache_full_ids[:prefix_len]
    continuation = torch.tensor(
        [int(token) for token in continuation_rows[0]],
        dtype=prefix.dtype,
    )
    processor._cache_full_ids = torch.cat((prefix, continuation), dim=0)
    processor._cache_prev_len = int(processor._cache_full_ids.numel())
