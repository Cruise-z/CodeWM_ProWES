# waterfallLP.py
# Wrap only the logits processor while staying aligned with the official implementation:
# - Reuse the official PerturbationProcessor and WatermarkingFn* (to generate the same phi)
# - Keep sampling-chain order under external control (sampling warper first, waterfall after)
# - Move detection/verify capability into the processor class without changing the original embedding logic
import numpy as np
from typing import Iterable, Optional, List, Union, Dict, Any, cast
import torch
import time as _time
from transformers.generation.logits_process import LogitsProcessor

from .WatermarkerBase import PerturbationProcessor, Watermarker
from .WatermarkingFnFourier import WatermarkingFnFourier
from .WatermarkingFnSquare import WatermarkingFnSquare


def _resolve_vocab_size(
    tokenizer=None,
    vocab_ids: Optional[Iterable[int]] = None,
) -> int:
    """
    Determine N consistently with the official implementation (apply perturbation to scores[:, :N]).
    Priority: tokenizer.vocab_size > dense vocab_ids.
    If vocab_ids are not a dense 0..N-1 range, tokenizer must be passed explicitly.
    """
    if tokenizer is not None and getattr(tokenizer, "vocab_size", None) is not None:
        return int(tokenizer.vocab_size)

    if vocab_ids is not None:
        ids = list(vocab_ids)
        if not ids:
            raise ValueError("vocab_ids is empty; please pass tokenizer explicitly")
        mn, mx = min(ids), max(ids)
        # Density check: must be [0, 1, ..., mx] with mn == 0 and no gaps
        if mn == 0 and len(set(ids)) == (mx + 1):
            return mx + 1
        raise ValueError(
            "Detected non-dense vocab_ids (not a continuous range from 0 to N-1). "
            "Please pass tokenizer explicitly (N=tokenizer.vocab_size) to stay fully aligned with the official implementation"
        )

    raise ValueError("Unable to determine N; please pass tokenizer or dense vocab_ids")


class WaterfallLogitsProcessor(LogitsProcessor):
    """
    - Generate phi (Fourier/Square) and inject it into the official PerturbationProcessor
    - Built-in auto-reset: detect the start of a new generation round and automatically reset(n_gram)
      * By default, detection is batch-level; row-wise detection is also supported and resets the whole batch
        when any sample restarts, ensuring no new sequence is missed (the official behavior is batch-level reset).
    - Offline zero-argument detection: detect_last()
      * The processor continuously caches continuation tokens newly generated in the current round (excluding the prompt)
        inside __call__, so the server can invoke detection directly after generation ends.
    """

    def __init__(
        self,
        *,
        id_mu: int,
        k_p: int,
        kappa: float,
        n_gram: int = 2,
        wm_fn: str = "fourier",
        # The next two parameters are used to determine N (see _resolve_vocab_size for priority)
        tokenizer=None,
        vocab_ids: Optional[Iterable[int]] = None,
        # Dynamic batch control
        auto_reset: bool = True,
        detect_mode: str = "batch",  # "batch" | "row_any"
        # Detection dependency (used for tokenization in Watermarker.verify)
        det_tokenizer=None,          # Can be an HF tokenizer or a model ID string
        # Hard cap on cache size (useful for very long generations to limit memory)
        cache_hard_limit_tokens: Optional[int] = None,
    ):
        # ---- 1) Determine N in alignment with the official implementation ----
        self._N = _resolve_vocab_size(tokenizer=tokenizer, vocab_ids=vocab_ids)

        # ---- 2) Construct the official logits processor and inject phi ----
        self._proc = PerturbationProcessor(N=self._N, id=id_mu)

        Fn = WatermarkingFnFourier if wm_fn.lower() == "fourier" else WatermarkingFnSquare
        phi = Fn(id=id_mu, k_p=int(k_p), N=self._N, kappa=float(kappa)).phi
        self._proc.set_phi(phi)

        # ---- 3) n-gram and auto-reset state ----
        self._n_gram = int(n_gram)
        self._auto_reset = bool(auto_reset)
        if detect_mode not in ("batch", "row_any"):
            raise ValueError("detect_mode must be either 'batch' or 'row_any'")
        self._detect_mode = detect_mode  # "batch": monotonically increasing batch length; "row_any": reset whole batch when any row restarts

        # Record the previous length to detect a new generation round
        self._prev_len_batch: Optional[int] = None
        self._prev_len_rows: Optional[List[int]] = None

        # Initial reset (equivalent to the official "reset before generation")
        self._proc.reset(self._n_gram)

        # ---- 4) Persistent detection-related configuration/state (does not affect embedding path) ----
        self._id_mu = int(id_mu)
        self._kappa = float(kappa)
        self._wm_fn = str(wm_fn)
        self._det_tokenizer = det_tokenizer if det_tokenizer is not None else tokenizer
        self._wm: Optional[Watermarker] = None  # Lazy initialization, created on first detect

        # ---- 5) Side-channel cache (accumulates continuation tokens only during the current generation round) ----
        self._cache_rows_ids: Optional[List[List[int]]] = None  # Accumulated newly generated tokens for each row
        self._cache_limit = None if cache_hard_limit_tokens is None else int(cache_hard_limit_tokens)
        # Record the previous length per row to precisely extract new spans and avoid counting prompt-tail tokens
        self._prev_seen_len_rows: Optional[List[int]] = None

        # ---- Performance counters (pure logits-processor overhead, accumulated per __call__) ----
        self._lp_time_s: float = 0.0
        self._lp_calls: int = 0

    # Optional: explicit manual reset, useful if you want to coordinate with an external lifecycle
    def reset(self, n_gram: Optional[int] = None):
        if n_gram is not None:
            self._n_gram = int(n_gram)
        self._proc.reset(self._n_gram)
        self._prev_len_batch = None
        self._prev_len_rows = None
        self._cache_rows_ids = None  # Clear side-channel cache
        self._prev_seen_len_rows = None
        # timing counters are not reset here intentionally

    # —— Private: reset local caches when a new generation round is detected —— #
    def _reset_local_caches(self, bsz: int):
        self._cache_rows_ids = [[] for _ in range(bsz)]

    # HF LogitsProcessor interface
    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor):
        bsz, cur_len = int(input_ids.shape[0]), int(input_ids.shape[1])

        need_reset = False
        if self._auto_reset:
            if self._detect_mode == "batch":
                # Batch-level detection: length should strictly increase; otherwise treat it as a new generation round
                if self._prev_len_batch is None or cur_len <= self._prev_len_batch:
                    need_reset = True
                self._prev_len_batch = cur_len
            else:  # "row_any"
                if self._prev_len_rows is None or len(self._prev_len_rows) != bsz:
                    need_reset = True
                    self._prev_len_rows = [cur_len] * bsz
                else:
                    if any(cur_len <= pl for pl in self._prev_len_rows):
                        need_reset = True
                        self._prev_len_rows = [cur_len] * bsz
                    else:
                        self._prev_len_rows = [cur_len] * bsz

        if need_reset:
            # Reset the official perturbation state
            self._proc.reset(self._n_gram)
            # Reset the side-channel cache
            self._reset_local_caches(bsz)
            self._prev_seen_len_rows = [int(input_ids.shape[1])] * bsz  # New round: baseline is the current length, excluding prompt-tail tokens

        # If the cache has not been initialized yet, for example when auto_reset=False or on the first call
        if self._cache_rows_ids is None or len(self._cache_rows_ids) != bsz:
            self._reset_local_caches(bsz)
        if self._prev_seen_len_rows is None or len(self._prev_seen_len_rows) != bsz:
            self._prev_seen_len_rows = [cur_len] * bsz  # First call only sets the baseline and does not append

        # —— Precisely accumulate the continuation span newly added in this step into the cache —— #
        for i in range(bsz):
            prev = self._prev_seen_len_rows[i]
            if cur_len > prev:
                # Only append the truly new tokens in [prev:cur_len) to the cache
                new_span = input_ids[i, prev:cur_len].tolist()
                if new_span:
                    self._cache_rows_ids[i].extend(int(t) for t in new_span)
                    # Hard-cap trimming (optional)
                    if self._cache_limit is not None and len(self._cache_rows_ids[i]) > self._cache_limit:
                        overflow = len(self._cache_rows_ids[i]) - self._cache_limit
                        if overflow > 0:
                            self._cache_rows_ids[i] = self._cache_rows_ids[i][overflow:]
        # Update the baseline length
        self._prev_seen_len_rows = [cur_len] * bsz

        # Actual perturbation: delegate to the official implementation and time only the perturbation logic itself
        t0 = _time.perf_counter()
        try:
            out = self._proc(input_ids, scores)
            return out
        finally:
            # Best-effort timing: must never affect generation behavior
            try:
                self._lp_time_s += float(_time.perf_counter() - t0)
                self._lp_calls += 1
            except Exception:
                pass

    def timing(self) -> Dict[str, Any]:
        """
        Return accumulated logits-processor runtime (waterfall perturbation part).
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

    # ------------------- Offline zero-argument detection ------------------- #
    def _ensure_watermarker(self) -> None:
        """
        Lazily initialize Watermarker, triggered only when detect_last is called.
        Note: if N was inferred from vocab_ids and tokenizer was not provided,
        you must explicitly provide the tokenizer needed for detection through det_tokenizer
        during construction (either an HF tokenizer instance or a model ID).
        """
        if self._wm is not None:
            return
        if self._det_tokenizer is None:
            raise ValueError(
                "WaterfallLogitsProcessor.detect_last(): det_tokenizer/tokenizer is required to construct Watermarker."
            )
        Fn = WatermarkingFnFourier if self._wm_fn.lower() == "fourier" else WatermarkingFnSquare
        # In verify, k_p=None can be used for automatic extraction; here k_p=1 is used as a placeholder to stay aligned with the official Detector
        self._wm = Watermarker(
            tokenizer=self._det_tokenizer,
            id=int(self._id_mu),
            kappa=float(self._kappa),
            k_p=1,
            n_gram=int(self._n_gram),
            watermarkingFnClass=cast(Any, Fn),
        )

    def _decode_ids_to_text(self, ids: List[int]) -> str:
        if not ids:
            return ""
        tk = self._det_tokenizer
        # Prefer standard HF decode first
        if hasattr(tk, "decode") and callable(getattr(tk, "decode")):
            return tk.decode(ids, skip_special_tokens=True)  # type: ignore[attr-defined]
        # Fallback: try ids -> tokens -> string
        if (
            hasattr(tk, "convert_ids_to_tokens")
            and hasattr(tk, "convert_tokens_to_string")
        ):
            toks = tk.convert_ids_to_tokens(ids)  # type: ignore[attr-defined]
            return tk.convert_tokens_to_string(toks)  # type: ignore[attr-defined]
        raise ValueError("det_tokenizer cannot decode token ids; please pass an HF tokenizer instance in the builder.")

    def _cached_texts(self) -> List[str]:
        """
        Decode the cached continuation tokens into text row by row.
        Return an empty list if there is no cache or the cache is empty.
        """
        if self._cache_rows_ids is None:
            return []
        return [self._decode_ids_to_text(row) for row in self._cache_rows_ids]

    def detect_last(self) -> Dict[str, Any]:
        """
        Zero-argument detection: compute q_score row by row from the continuation text currently cached in the processor.
        Returns a dictionary:
          - "q_score": float or List[float] (single/multi-sample)
          - may include "k_p_extracted" (depending on the underlying Watermarker)
        It can be called after one generation round finishes, with no need to pass any parameters through the server.
        """
        self._ensure_watermarker()
        texts = self._cached_texts()
        if not texts:
            return {"error": "no_cached_tokens", "q_score": 0.0}

        res = self._wm.verify(  # type: ignore[union-attr]
            texts,
            id=[int(self._id_mu)],
            k_p=None,  # Allow automatic extraction of k_p
            return_extracted_k_p=True,
            return_ranking=False,
            return_counts=False,
        )

        out: Dict[str, Any] = {}
        if isinstance(res, dict):
            q = np.asarray(res.get("q_score"))
            if q.ndim >= 1:
                try:
                    q_vec = np.squeeze(q)
                    if q_vec.ndim != 1 or q_vec.shape[0] != len(texts):
                        if q.ndim == 3 and q.shape[1] >= 1 and q.shape[2] >= 1:
                            q_vec = q[:, 0, 0]
                        elif q.ndim == 2 and q.shape[1] >= 1:
                            q_vec = q[:, 0]
                        else:
                            q_vec = q.reshape(len(texts), -1)[:, 0]
                except Exception:
                    q_vec = q
            else:
                q_vec = q

            if len(texts) == 1:
                out["q_score"] = float(np.asarray(q_vec).reshape(-1)[0])
            else:
                out["q_score"] = [float(x) for x in np.asarray(q_vec).reshape(-1)]

            if "k_p_extracted" in res:
                kpe = np.asarray(res["k_p_extracted"])
                if kpe.ndim == 2 and kpe.shape[1] >= 1:
                    kpe = kpe[:, 0]
                out["k_p_extracted"] = (
                    int(kpe.reshape(-1)[0]) if len(texts) == 1 else [int(x) for x in kpe.reshape(-1)]
                )
        else:
            q = np.asarray(res)
            if q.ndim == 3 and q.shape[1] >= 1 and q.shape[2] >= 1:
                q_vec = q[:, 0, 0]
            elif q.ndim == 2 and q.shape[1] >= 1:
                q_vec = q[:, 0]
            else:
                q_vec = np.squeeze(q)
                if q_vec.ndim != 1:
                    q_vec = q.reshape(len(texts), -1)[:, 0]
            out["q_score"] = (
                float(np.asarray(q_vec).reshape(-1)[0]) if len(texts) == 1 else [float(x) for x in np.asarray(q_vec).reshape(-1)]
            )
        # Clear the cache after detection to avoid affecting the next round
        self.clear_cached()
        self._prev_seen_len_rows = None
        return out

    def clear_cached(self) -> None:
        """Clear the continuation cache for the current round without affecting perturbation state."""
        if self._cache_rows_ids is not None:
            for i in range(len(self._cache_rows_ids)):
                self._cache_rows_ids[i].clear()
