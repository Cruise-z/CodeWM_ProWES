# sweetLP.py
from __future__ import annotations
from typing import Any, List, Dict, Optional
from math import sqrt

import torch
from ..timing import (
    detection_state_enabled,
    processor_timing_enabled,
    synchronized_perf_counter,
)
from torch import Tensor

# Reuse the WLLM base while preserving SWEET embedding behavior.
from ..wllm.watermark import WatermarkLogitsProcessor
import scipy.stats


class SWEETLogitsProcessor(WatermarkLogitsProcessor):
    """
    SWEET processor with integrated embedding and offline detection.
    - Preserve entropy-gated green-list biasing.
    - Cache prefix_len, full_ids, and per-step entropy at runtime.
    - Recompute detector entropy from the configured detector sequence, matching the
      standalone SWEET detection protocol instead of relying on generation
      side information.
    """

    def __init__(
        self,
        *args,
        entropy_threshold: float = 0.9,
        tokenizer=None,
        model=None,
        device=None,
        z_threshold: float = 4.0,
        ignore_repeated_bigrams: bool = False,
        detector_scope: str = "generation_conditioned",
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        # SWEET configuration; it does not alter upstream semantics.
        self.entropy_threshold = float(entropy_threshold)
        self._tokenizer = tokenizer
        self._model = model
        self._device = device
        self._z_threshold = float(z_threshold)
        self._ignore_repeated_bigrams = bool(ignore_repeated_bigrams)
        if detector_scope not in ("generation_conditioned", "continuation"):
            raise ValueError(
                "SWEET detector_scope must be 'generation_conditioned' or 'continuation'"
            )
        self._detector_scope = detector_scope
        if getattr(self, "rng", None) is None:
            self.rng = torch.Generator()

        # Runtime cache for zero-argument detection.
        self._cache_prev_len: Optional[int] = None
        self._cache_prefix_len: Optional[int] = None
        self._cache_full_ids: Optional[torch.LongTensor] = None
        self._cache_entropy: List[float] = []
        
        # ---- Performance counters (pure logits-processor overhead, accumulated per __call__) ----
        self._lp_time_s: float = 0.0
        self._lp_calls: int = 0

        # simple_1 seeding requires at least one prefix token.
        self._min_prefix_len: int = 1 if getattr(self, "seeding_scheme", "simple_1") == "simple_1" else 1

    # Preserve embedding behavior and append caching only.
    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor) -> torch.FloatTensor:
        timing_enabled = processor_timing_enabled()
        t0 = synchronized_perf_counter(scores) if timing_enabled else 0.0
        try:
            # Initialize the RNG lazily.
            if self.rng is None:
                self.rng = torch.Generator()

            # 1) Compute the green list for each sample.
            batched_greenlist_ids = [None for _ in range(input_ids.shape[0])]
            for b_idx in range(input_ids.shape[0]):
                greenlist_ids = self._get_greenlist_ids(input_ids[b_idx])
                batched_greenlist_ids[b_idx] = greenlist_ids

            green_tokens_mask = self._calc_greenlist_mask(scores=scores, greenlist_token_ids=batched_greenlist_ids)

            # 2) Compute next-token entropy as defined by SWEET.
            raw_probs = torch.softmax(scores, dim=-1)
            ent = -torch.where(raw_probs > 0, raw_probs * raw_probs.log(), raw_probs.new([0.0])).sum(dim=-1)  # [B]
            entropy_mask = (ent > self.entropy_threshold).view(-1, 1)

            # 3) Apply the green-list bias only at high-entropy steps.
            green_tokens_mask = green_tokens_mask * entropy_mask
            scores = self._bias_greenlist_logits(scores=scores, greenlist_mask=green_tokens_mask, greenlist_bias=self.delta)
        finally:
            if timing_enabled:
                try:
                    self._lp_time_s += float(synchronized_perf_counter(scores) - t0)
                    self._lp_calls += 1
                except Exception:
                    pass

        # 4) Cache the prefix length, full IDs, and per-step entropy.
        if detection_state_enabled():
            try:
                bsz, cur_len = int(input_ids.shape[0]), int(input_ids.shape[1])
                if bsz == 1:
                    if self._cache_prev_len is None or cur_len <= self._cache_prev_len:
                        # A shorter/equal sequence starts a new generation.
                        self._cache_prefix_len = cur_len
                        self._cache_entropy = []
                    self._cache_prev_len = cur_len
                    # Full sequence through the current step.
                    self._cache_full_ids = input_ids[0].detach().to("cpu").clone()
                    # Entropy aligned with the token about to be sampled.
                    self._cache_entropy.append(float(ent[0].item()))
            except Exception:
                pass  # Cache failures must not affect generation.

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

    # Offline zero-argument detection aligned with SweetDetector.
    @staticmethod
    def _compute_z_score(observed_green: int, T: int, gamma: float) -> float:
        expected = gamma
        numer = observed_green - expected * T
        denom = sqrt(max(1e-12, T * expected * (1 - expected)))
        return float(numer / denom)

    @staticmethod
    def _compute_p_value(z: float) -> float:
        return float(scipy.stats.norm.sf(z))

    def _detector_entropy(self, input_ids: Tensor, prefix_len: int) -> tuple[List[float], Dict[str, Any]]:
        """Recompute per-token entropy from the configured detector sequence.

        A causal LM logit at position ``i - 1`` predicts token ``i``.  The
        prompt is therefore retained as model context, while only continuation
        positions are returned to the SWEET scoring gate.  Chunked float32
        entropy calculation avoids holding several full-vocabulary temporary
        tensors at once.
        """
        if self._model is None or self._device is None:
            raise RuntimeError("SWEET detection requires the generation model and device")

        prefix_len = int(prefix_len)
        sequence_length = int(input_ids.numel())
        if prefix_len < 1 or sequence_length <= prefix_len:
            raise ValueError(
                "SWEET detector requires a prefix and scoreable suffix: "
                f"prefix_len={prefix_len}, sequence_length={sequence_length}"
            )

        model_ids = input_ids.to(self._device, non_blocking=True).unsqueeze(0)
        with torch.inference_mode():
            outputs = self._model(
                input_ids=model_ids,
                use_cache=False,
                return_dict=True,
            )
        logits = outputs.logits
        if logits.ndim != 3 or int(logits.shape[0]) != 1:
            raise ValueError(
                "SWEET detector expected model logits with shape [1, sequence, vocab], "
                f"got {tuple(logits.shape)}"
            )

        predictive_logits = logits[0, prefix_len - 1 : sequence_length - 1]
        expected = sequence_length - prefix_len
        if int(predictive_logits.shape[0]) != expected:
            raise ValueError(
                "SWEET detector entropy alignment failed: "
                f"expected={expected}, got={int(predictive_logits.shape[0])}"
            )

        entropy_chunks = []
        for chunk in predictive_logits.split(64, dim=0):
            log_probabilities = torch.log_softmax(chunk.float(), dim=-1)
            entropy_chunks.append(
                -(log_probabilities.exp() * log_probabilities).sum(dim=-1)
            )
        continuation_entropy = torch.cat(entropy_chunks).detach().cpu()
        values = [float(value) for value in continuation_entropy.tolist()]
        qualified = sum(value > self.entropy_threshold for value in values)
        stats: Dict[str, Any] = {
            "source": "detector_model_forward",
            "continuation_tokens": len(values),
            "qualified_tokens": int(qualified),
            "threshold": float(self.entropy_threshold),
            "minimum": float(min(values)),
            "maximum": float(max(values)),
            "mean": float(sum(values) / len(values)),
        }
        return [0.0] * prefix_len + values, stats

    def _score_sequence(
        self,
        input_ids: Tensor,
        prefix_len: int,
        entropy: List[float],
        *,
        return_num_tokens_scored: bool = True,
        return_num_green_tokens: bool = True,
        return_watermarking_fraction: bool = True,
        return_green_fraction: bool = True,
        return_green_token_mask: bool = False,
        return_z_score: bool = True,
        return_p_value: bool = True,
    ) -> Dict:
        if self._ignore_repeated_bigrams:
            raise NotImplementedError(
                "ignore_repeated_bigrams=True is not implemented upstream"
            )

        out: Dict = {}
        prefix_len = max(self._min_prefix_len, int(prefix_len))
        num_tokens_generated = int(len(input_ids) - prefix_len)
        if num_tokens_generated < 1:
            out["invalid"] = True
            return out

        # Count only positions above the entropy threshold.
        if len(entropy) != len(input_ids):
            # Pad the prefix with zeros and retain recorded entropy order.
            if len(entropy) == num_tokens_generated:
                entropy = [0.0] * prefix_len + list(entropy)
            else:
                raise ValueError(f"entropy length mismatch: got {len(entropy)} vs ids {len(input_ids)}")

        scored_positions = [i for i in range(prefix_len, len(input_ids)) if entropy[i] > self.entropy_threshold]
        num_tokens_scored = len(scored_positions)
        if num_tokens_scored < 1:
            # Treat the sequence as approximately human-generated.
            return {
                "num_tokens_generated": num_tokens_generated,
                "num_tokens_scored": 0,
                "num_green_tokens": 0,
                "watermarking_fraction": 0.0,
                "green_fraction": 0.0,
                "z_score": -100.0,
                "p_value": 1.0,
            }

        green_token_count, green_token_mask = 0, []
        for idx in range(prefix_len, len(input_ids)):
            curr_token = input_ids[idx]
            greenlist_ids = self._get_greenlist_ids(input_ids[:idx])
            if entropy[idx] > self.entropy_threshold:
                # Preserve the upstream tensor-membership implementation.
                if curr_token in greenlist_ids:
                    green_token_count += 1
                    green_token_mask.append(True)
                else:
                    green_token_mask.append(False)
            else:
                green_token_mask.append(False)

        out["num_tokens_generated"] = num_tokens_generated
        if return_num_tokens_scored:
            out["num_tokens_scored"] = num_tokens_scored
        if return_num_green_tokens:
            out["num_green_tokens"] = int(green_token_count)
        if return_watermarking_fraction:
            out["watermarking_fraction"] = float(num_tokens_scored / max(1, num_tokens_generated))
        if return_green_fraction:
            out["green_fraction"] = float(green_token_count / max(1, num_tokens_scored))
        if return_z_score:
            z = self._compute_z_score(green_token_count, num_tokens_scored, float(self.gamma))
            out["z_score"] = z
        if return_p_value:
            z = out.get("z_score")
            if z is None:
                z = self._compute_z_score(green_token_count, num_tokens_scored, float(self.gamma))
            out["p_value"] = self._compute_p_value(float(z))
        if return_green_token_mask:
            out["green_token_mask"] = green_token_mask
        return out

    def detect_last(self) -> Dict:
        """
        Detect from cached token IDs with entropy independently recomputed by
        the model over the configured detector token scope.
        """
        if self._cache_full_ids is None or self._cache_prefix_len is None:
            raise RuntimeError("No cached sequence for detection. Generate with this processor first.")

        full_ids: Tensor = self._cache_full_ids
        generation_prefix_len: int = int(self._cache_prefix_len)
        if self._detector_scope == "continuation":
            detector_ids = full_ids[generation_prefix_len:]
            detector_prefix_len = self._min_prefix_len
        else:
            detector_ids = full_ids
            detector_prefix_len = generation_prefix_len
        entropy_full, entropy_stats = self._detector_entropy(
            detector_ids,
            detector_prefix_len,
        )

        out: Dict = {}
        score = self._score_sequence(
            input_ids=detector_ids,
            prefix_len=detector_prefix_len,
            entropy=entropy_full,
            return_num_tokens_scored=True,
            return_num_green_tokens=True,
            return_watermarking_fraction=True,
            return_green_fraction=True,
            return_green_token_mask=False,
            return_z_score=True,
            return_p_value=True,
        )
        out.update(score)
        out["entropy"] = entropy_stats
        out["detector_scope"] = self._detector_scope
        out["detector_input_tokens"] = int(detector_ids.numel())

        thr = float(self._z_threshold)
        if score.pop("invalid", False):
            out["invalid"] = True
            return out
        pred = bool(float(score["z_score"]) > thr)
        out["prediction"] = pred
        if pred:
            out["confidence"] = float(1.0 - float(score.get("p_value", 1.0)))
        
        # Clear cached trace state after detection.
        self._cache_full_ids = None
        self._cache_prefix_len = None
        self._cache_prev_len = None
        self._cache_entropy = []
        return out


def build_codewm(resources, params):
    """Construct the CodeWM wrapper from declared framework resources."""
    ignore_repeated_bigrams = params.get("ignore_repeated_bigrams", False)
    if not isinstance(ignore_repeated_bigrams, bool):
        raise ValueError("SWEET ignore_repeated_bigrams must be a JSON boolean")
    if ignore_repeated_bigrams:
        raise ValueError(
            "SWEET ignore_repeated_bigrams=true is not implemented by this adapter"
        )
    return SWEETLogitsProcessor(
        vocab=resources.vocab_ids(),
        gamma=params.get("gamma", 0.5),
        delta=params.get("delta", 1),
        entropy_threshold=params.get("entropy_threshold", 0.9),
        tokenizer=resources.tokenizer,
        model=resources.model,
        device=resources.device,
        z_threshold=params.get("z_threshold", 4.0),
        ignore_repeated_bigrams=ignore_repeated_bigrams,
        detector_scope=str(params.get("detector_scope", "generation_conditioned")),
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
