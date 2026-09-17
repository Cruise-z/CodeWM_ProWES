# waterfallLP.py
# Logits-processor wrapper aligned with the official implementation:
# - reuse PerturbationProcessor and WatermarkingFn* to generate the same phi;
# - retain externally controlled sampling order (warpers before Waterfall);
# - integrate verification without changing embedding behavior.
import numpy as np
from typing import Iterable, Optional, List, Union, Dict, Any, cast
import torch
from transformers.generation.logits_process import LogitsProcessor

from ..timing import synchronized_perf_counter

from .WatermarkerBase import PerturbationProcessor, Watermarker
from .WatermarkingFnFourier import WatermarkingFnFourier
from .WatermarkingFnSquare import WatermarkingFnSquare


def _resolve_vocab_size(
    tokenizer=None,
    vocab_ids: Optional[Iterable[int]] = None,
) -> int:
    """
    Resolve N consistently with the official implementation, preferring
    tokenizer.vocab_size over a dense vocab_ids range. A tokenizer is required
    when vocab_ids is not exactly the dense interval [0, N).
    """
    if tokenizer is not None and getattr(tokenizer, "vocab_size", None) is not None:
        return int(tokenizer.vocab_size)

    if vocab_ids is not None:
        ids = list(vocab_ids)
        if not ids:
            raise ValueError("vocab_ids is empty; provide a tokenizer explicitly")
        mn, mx = min(ids), max(ids)
        # Dense IDs must equal [0, 1, ..., max_id] without gaps.
        if mn == 0 and len(set(ids)) == (mx + 1):
            return mx + 1
        raise ValueError(
            "vocab_ids is not the dense interval [0, N); provide a tokenizer "
            "explicitly to match the official implementation"
        )

    raise ValueError("cannot resolve N; provide a tokenizer or dense vocab_ids")


class WaterfallLogitsProcessor(LogitsProcessor):
    """
    Generate Fourier/Square phi through the official PerturbationProcessor,
    detect generation boundaries for automatic n-gram reset, and expose
    zero-argument offline detection. The processor caches only continuation
    tokens from the current generation.
    """

    def __init__(
        self,
        *,
        id_mu: int,
        k_p: int,
        kappa: float,
        n_gram: int = 2,
        wm_fn: str = "fourier",
        # Inputs used to resolve N; see _resolve_vocab_size.
        tokenizer=None,
        vocab_ids: Optional[Iterable[int]] = None,
        # Dynamic batch control.
        auto_reset: bool = True,
        detect_mode: str = "batch",  # "batch" | "row_any"
        # Tokenizer used by Watermarker.verify.
        det_tokenizer=None,          # HF tokenizer instance or model ID.
        # Optional cache cap for very long generations.
        cache_hard_limit_tokens: Optional[int] = None,
    ):
        # 1) Resolve N consistently with the official code.
        self._N = _resolve_vocab_size(tokenizer=tokenizer, vocab_ids=vocab_ids)

        # 2) Construct the official processor and inject phi.
        self._proc = PerturbationProcessor(N=self._N, id=id_mu)

        Fn = WatermarkingFnFourier if wm_fn.lower() == "fourier" else WatermarkingFnSquare
        phi = Fn(id=id_mu, k_p=int(k_p), N=self._N, kappa=float(kappa)).phi
        self._proc.set_phi(phi)

        # 3) n-gram and automatic-reset state.
        self._n_gram = int(n_gram)
        self._auto_reset = bool(auto_reset)
        if detect_mode not in ("batch", "row_any"):
            raise ValueError("detect_mode must be 'batch' or 'row_any'")
        self._detect_mode = detect_mode

        # Previous lengths identify the start of a new generation.
        self._prev_len_batch: Optional[int] = None
        self._prev_len_rows: Optional[List[int]] = None

        # Initial reset, equivalent to the official pre-generation reset.
        self._proc.reset(self._n_gram)

        # 4) Persistent detection state; embedding is unaffected.
        self._id_mu = int(id_mu)
        self._kappa = float(kappa)
        self._wm_fn = str(wm_fn)
        self._det_tokenizer = det_tokenizer if det_tokenizer is not None else tokenizer
        self._wm: Optional[Watermarker] = None  # Lazily created on detection.

        # 5) Per-row continuation-token cache for the current generation.
        self._cache_rows_ids: Optional[List[List[int]]] = None
        self._cache_limit = None if cache_hard_limit_tokens is None else int(cache_hard_limit_tokens)
        # Previous per-row lengths allow exact extraction of new spans.
        self._prev_seen_len_rows: Optional[List[int]] = None

        # ---- Performance counters (pure logits-processor overhead, accumulated per __call__) ----
        self._lp_time_s: float = 0.0
        self._lp_calls: int = 0

    # Optional explicit reset for an externally managed lifecycle.
    def reset(self, n_gram: Optional[int] = None):
        if n_gram is not None:
            self._n_gram = int(n_gram)
        self._proc.reset(self._n_gram)
        self._prev_len_batch = None
        self._prev_len_rows = None
        self._cache_rows_ids = None
        self._prev_seen_len_rows = None
        # timing counters are not reset here intentionally

    # Reset local caches when a new generation starts.
    def _reset_local_caches(self, bsz: int):
        self._cache_rows_ids = [[] for _ in range(bsz)]

    # Hugging Face LogitsProcessor interface.
    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor):
        bsz, cur_len = int(input_ids.shape[0]), int(input_ids.shape[1])

        need_reset = False
        if self._auto_reset:
            if self._detect_mode == "batch":
                # Batch lengths must increase strictly within one generation.
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
            # Reset official perturbation state.
            self._proc.reset(self._n_gram)
            # Reset side-channel caches.
            self._reset_local_caches(bsz)
            self._prev_seen_len_rows = [int(input_ids.shape[1])] * bsz

        # Initialize caches on the first call or when auto-reset is disabled.
        if self._cache_rows_ids is None or len(self._cache_rows_ids) != bsz:
            self._reset_local_caches(bsz)
        if self._prev_seen_len_rows is None or len(self._prev_seen_len_rows) != bsz:
            self._prev_seen_len_rows = [cur_len] * bsz

        # Append exactly the continuation span introduced at this step.
        for i in range(bsz):
            prev = self._prev_seen_len_rows[i]
            if cur_len > prev:
                # Only [prev:cur_len) contains newly introduced tokens.
                new_span = input_ids[i, prev:cur_len].tolist()
                if new_span:
                    self._cache_rows_ids[i].extend(int(t) for t in new_span)
                    # Apply the optional hard cache limit.
                    if self._cache_limit is not None and len(self._cache_rows_ids[i]) > self._cache_limit:
                        overflow = len(self._cache_rows_ids[i]) - self._cache_limit
                        if overflow > 0:
                            self._cache_rows_ids[i] = self._cache_rows_ids[i][overflow:]
        # Update baseline lengths.
        self._prev_seen_len_rows = [cur_len] * bsz

        # Delegate perturbation to the official implementation and time it.
        t0 = synchronized_perf_counter(scores)
        try:
            out = self._proc(input_ids, scores)
            return out
        finally:
            # Best-effort timing: must never affect generation behavior
            try:
                self._lp_time_s += float(synchronized_perf_counter(scores) - t0)
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

    # Offline zero-argument detection.
    def _ensure_watermarker(self) -> None:
        """
        Lazily initialize Watermarker on the first detect_last() call. When N
        was inferred from vocab_ids, det_tokenizer must still provide the
        tokenizer required for verification.
        """
        if self._wm is not None:
            return
        if self._det_tokenizer is None:
            raise ValueError(
                "WaterfallLogitsProcessor.detect_last() requires det_tokenizer/tokenizer"
            )
        Fn = WatermarkingFnFourier if self._wm_fn.lower() == "fourier" else WatermarkingFnSquare
        # k_p is a constructor placeholder; verify may extract it automatically.
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
        # Prefer standard Hugging Face decoding.
        if hasattr(tk, "decode") and callable(getattr(tk, "decode")):
            return tk.decode(ids, skip_special_tokens=True)  # type: ignore[attr-defined]
        # Fallback to IDs -> tokens -> string.
        if (
            hasattr(tk, "convert_ids_to_tokens")
            and hasattr(tk, "convert_tokens_to_string")
        ):
            toks = tk.convert_ids_to_tokens(ids)  # type: ignore[attr-defined]
            return tk.convert_tokens_to_string(toks)  # type: ignore[attr-defined]
        raise ValueError(
            "det_tokenizer cannot decode token IDs; provide an HF tokenizer instance"
        )

    def _cached_texts(self) -> List[str]:
        """Decode cached continuation tokens row by row.

        Return an empty list when no non-empty continuation is cached.
        """
        if self._cache_rows_ids is None:
            return []
        return [self._decode_ids_to_text(row) for row in self._cache_rows_ids]

    def detect_last(self) -> Dict[str, Any]:
        """Score each cached continuation from the latest generation round.

        The result contains ``q_score`` as a scalar or list and may contain
        ``k_p_extracted`` when supplied by Watermarker. No server-side
        arguments are required.
        """
        self._ensure_watermarker()
        texts = self._cached_texts()
        if not texts:
            return {"error": "no_cached_tokens", "q_score": 0.0}

        res = self._wm.verify(  # type: ignore[union-attr]
            texts,
            id=[int(self._id_mu)],
            k_p=None,  # Allow Watermarker to infer k_p.
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
        # Clear cached text so the next generation starts cleanly.
        self.clear_cached()
        self._prev_seen_len_rows = None
        return out

    def clear_cached(self) -> None:
        """Clear continuation state without changing perturbation state."""
        if self._cache_rows_ids is not None:
            for i in range(len(self._cache_rows_ids)):
                self._cache_rows_ids[i].clear()


def build_codewm(resources, params):
    """Construct WATERFALL with its declared tokenizer-base domain."""
    tokenizer = resources.tokenizer
    component = resources.component()
    if component.vocab_size != int(tokenizer.vocab_size):
        raise ValueError("WATERFALL requires the tokenizer_base runtime domain")
    return WaterfallLogitsProcessor(
        tokenizer=tokenizer,
        vocab_ids=component.vocab_ids,
        id_mu=int(params.get("id_mu", 42)),
        k_p=int(params.get("k_p", 1)),
        kappa=float(params.get("kappa", 2.0)),
        n_gram=int(params.get("n_gram", 2)),
        wm_fn=str(params.get("wm_fn", "fourier")),
        det_tokenizer=tokenizer,
        auto_reset=bool(params.get("auto_reset", True)),
        detect_mode=str(params.get("detect_mode", "batch")),
    )


def finalize_codewm_generation_evidence(processor, continuation_rows):
    """Replace detector evidence with complete model output IDs."""
    rows = [[int(token) for token in row] for row in continuation_rows]
    cache_limit = getattr(processor, "_cache_limit", None)
    if cache_limit is not None:
        limit = int(cache_limit)
        rows = [row[-limit:] if limit > 0 else [] for row in rows]
    processor._cache_rows_ids = rows
