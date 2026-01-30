"""
codeipLP.py

Wrapper that adapts the `codeip` project watermark processors into a logits-processor
that:
  (1) preserves the original logits-biasing behavior,
  (2) caches side-channel data during generation, and
  (3) exposes a zero-argument offline detector `detect_last()`.

This version keeps the upstream detection semantics as closely as possible while fixing
two practical issues:
  - Detection too slow (especially for long completions)
  - Detection output too large (GB-scale) due to serializing raw tensors / per-token info

Design choices (preserve logic, accelerate, shrink output):
  - RANDOM detection:
      * Equivalent to upstream `wm.py` + `WmProcessorRandomMessageModel.decode_with_input_ids` logic:
        decode the completion (output) tokens in encode_len-sized blocks and vote per bit.
      * Acceleration: only decode the minimal token prefix that can contribute to full blocks:
        need_tokens = available_message_num * encode_len.
      * Output: only score-related fields (no raw_info, no decoded message arrays).
  - PDA detection:
      * There is no upstream "decode" in the repo; detection here reports the same statistic
        implied by the PDA processor’s predicted_class -> token-set mechanism:
        green_fraction, expected count, z-score.
      * Acceleration: online accumulation during generation + O(1) membership via prebuilt sets.
      * Output: only score-related fields.

Notes:
  - This wrapper assumes batch=1 generation (same as your original caching approach).
  - If you reuse the same processor across multiple separate generations, call clear_cached()
    before starting a new generation to avoid boundary mis-detection.
"""
from __future__ import annotations
from typing import Any, Dict, Optional

import torch
import time as _time
from transformers import LogitsProcessor

from .message_model_processor import WmProcessorRandomMessageModel
from .PDA_model_processor import PDAProcessorMessageModel
from .message_model import RandomMessageModel
from .PDA_message_model import PDAMessageModel


class CodeipLogitsProcessor(LogitsProcessor):
    def __init__(
        self,
        processor: Optional[Any] = None,
        *,
        mode: str = "random",  # or 'pda'
        tokenizer=None,
        lm_tokenizer=None,
        pda_model=None,
        message=None,
        delta: float = 5.0,
        message_code_len: int = 20,
        encode_ratio: float = 10.0,
        top_k: int = 1000,
        gamma: float = 3.0,
        z_threshold: float = 0.0,
        device: Optional[torch.device] = None,
    ):
        # normalize device to torch.device when possible
        if device is not None and not isinstance(device, torch.device):
            try:
                device = torch.device(device)
            except Exception:
                pass

        # Wrap an existing processor, or build one.
        if processor is not None:
            self.processor = processor
            if isinstance(processor, WmProcessorRandomMessageModel):
                self._mode = "random"
            elif isinstance(processor, PDAProcessorMessageModel):
                self._mode = "pda"
            else:
                self._mode = str(mode)
        else:
            self._mode = str(mode)
            if self._mode == "random":
                if tokenizer is None:
                    raise ValueError("tokenizer required for building random message model")
                lm_tok = lm_tokenizer if lm_tokenizer is not None else tokenizer

                # RandomMessageModel expects a string device
                if device is None:
                    internal_dev = "cpu"
                elif isinstance(device, torch.device):
                    internal_dev = str(device)
                else:
                    internal_dev = device

                msg_model = RandomMessageModel(
                    tokenizer=tokenizer,
                    lm_tokenizer=lm_tok,
                    delta=delta,
                    message_code_len=message_code_len,
                    device=internal_dev,
                )
                self.processor = WmProcessorRandomMessageModel(
                    message=message or [0],
                    message_model=msg_model,
                    tokenizer=tokenizer,
                    encode_ratio=encode_ratio,
                    top_k=top_k,
                )
            elif self._mode == "pda":
                if tokenizer is None or pda_model is None:
                    raise ValueError("tokenizer and pda_model required for building pda processor")
                pda_msg_model = PDAMessageModel(tokenizer=tokenizer, pda_model=pda_model, delta=delta)
                self.processor = PDAProcessorMessageModel(
                    message_model=pda_msg_model,
                    tokenizer=tokenizer,
                    gamma=gamma,
                )
            else:
                raise ValueError(f"unknown mode: {mode}")

        # detection config
        self._z_threshold = float(z_threshold)
        self._gamma = float(gamma)
        self._device = device

        if self._device is not None:
            try:
                self._move_models_to_device(self._device)
            except Exception:
                pass

        # runtime caches (batch=1)
        self._cache_full_ids: Optional[torch.LongTensor] = None
        self._cache_prefix_len: Optional[int] = None
        self._cache_prev_len: Optional[int] = None

        # Performance counters (pure logits-processor overhead, accumulated per __call__)
        self._lp_time_s: float = 0.0
        self._lp_calls: int = 0

        # PDA online detection stats (avoid offline O(T^2))
        self._pda_prev_class: Optional[int] = None
        self._pda_last_pred: Optional[int] = None
        self._pda_T: int = 0
        self._pda_G: int = 0
        self._pda_sum_p: float = 0.0
        self._pda_sum_var: float = 0.0

        # Precomputed PDA sets/probabilities for speed
        self._pda_token_sets = None  # list[set[int]] or None
        self._pda_p = None           # list[float] or None

        # Hook PDA predictor to capture per-step predicted class
        self._pda_hooked: bool = False
        if self._mode == "pda":
            mm = getattr(self.processor, "message_model", None)
            if mm is not None:
                # Precompute sets and p_i once for O(1) membership and no per-step recompute.
                try:
                    tok = getattr(mm, "tokenizer", None)
                    token_sets = getattr(mm, "lex_and_tokenizer_id_list", None)
                    if tok is not None and token_sets is not None:
                        vocab_size = int(getattr(tok, "vocab_size", len(tok)))
                        self._pda_token_sets = [set(s) for s in token_sets]
                        if vocab_size > 0:
                            self._pda_p = [len(s) / float(vocab_size) for s in token_sets]
                except Exception:
                    self._pda_token_sets = None
                    self._pda_p = None

                if hasattr(mm, "get_pda_predictions"):
                    try:
                        orig_get = mm.get_pda_predictions

                        def _wrapped_get_pda_predictions(texts, *args, **kwargs):
                            preds = orig_get(texts, *args, **kwargs)
                            try:
                                if torch.is_tensor(preds) and preds.numel() > 0:
                                    self._pda_last_pred = int(preds[0].item())
                                elif hasattr(preds, "tolist") and not isinstance(preds, (str, bytes)):
                                    lst = preds.tolist()
                                    self._pda_last_pred = int(lst[0]) if len(lst) else None
                                else:
                                    self._pda_last_pred = int(preds[0]) if isinstance(preds, (list, tuple)) and len(preds) else None
                            except Exception:
                                self._pda_last_pred = None
                            return preds

                        mm.get_pda_predictions = _wrapped_get_pda_predictions
                        self._pda_hooked = True
                    except Exception:
                        self._pda_hooked = False

    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor) -> torch.FloatTensor:
        
        # Preserve upstream biasing behavior, and time ONLY the logits-processor path
        t0 = _time.perf_counter()
        try:
            out = self.processor(input_ids, scores)
        finally:
            # Best-effort timing: must never affect generation behavior
            try:
                self._lp_time_s += float(_time.perf_counter() - t0)
                self._lp_calls += 1
            except Exception:
                pass

        # Cache + PDA online stats (batch=1)
        try:
            bsz, cur_len = int(input_ids.shape[0]), int(input_ids.shape[1])
            if bsz != 1:
                return out

            is_new_gen = (self._cache_prev_len is None) or (cur_len <= self._cache_prev_len)
            if is_new_gen:
                self._cache_prefix_len = cur_len
                self._pda_prev_class = None
                self._pda_last_pred = None
                self._pda_T = 0
                self._pda_G = 0
                self._pda_sum_p = 0.0
                self._pda_sum_var = 0.0
            else:
                # Score the newly generated token using previous prefix class (PDA)
                if self._mode == "pda" and (cur_len == self._cache_prev_len + 1):
                    prev_class = self._pda_prev_class
                    if prev_class is not None and self._pda_token_sets is not None:
                        last_token = int(input_ids[0, -1].item())
                        self._pda_T += 1

                        # expected probability and variance
                        if self._pda_p is not None and 0 <= prev_class < len(self._pda_p):
                            p_i = float(self._pda_p[prev_class])
                            self._pda_sum_p += p_i
                            self._pda_sum_var += p_i * (1.0 - p_i)

                        # O(1) membership
                        if last_token in self._pda_token_sets[prev_class]:
                            self._pda_G += 1

            # Store current prefix predicted class for scoring next token
            if self._mode == "pda":
                self._pda_prev_class = self._pda_last_pred

            self._cache_prev_len = cur_len
            self._cache_full_ids = input_ids[0].detach().to("cpu").clone()
        except Exception:
            pass

        return out

    # ----------------- helpers -----------------

    def _move_models_to_device(self, device: Any) -> None:
        try:
            if not isinstance(device, torch.device):
                device = torch.device(device)
        except Exception:
            pass

        try:
            import torch.nn as nn
        except Exception:
            nn = None

        # processor itself
        try:
            if nn is not None and isinstance(self.processor, nn.Module):
                try:
                    self.processor.to(device)
                except Exception:
                    pass
        except Exception:
            pass

        mm = getattr(self.processor, "message_model", None)
        if mm is None:
            return

        # for legacy classes prefer string device
        try:
            dev_str = str(device)
            if nn is not None and isinstance(mm, nn.Module):
                try:
                    mm.to(device)
                except Exception:
                    pass
            else:
                try:
                    setattr(mm, "device", dev_str)
                except Exception:
                    pass
        except Exception:
            pass

        for attr in ("pda_model", "model", "lm_model", "transformer", "encoder"):
            m = getattr(mm, attr, None)
            if m is None:
                continue
            try:
                if nn is not None and isinstance(m, nn.Module):
                    try:
                        m.to(device)
                    except Exception:
                        pass
                else:
                    try:
                        setattr(m, "device", str(device))
                    except Exception:
                        pass
            except Exception:
                continue

    def _encode_len(self) -> Optional[int]:
        # upstream: encode_len = int(message_code_len * encode_ratio)
        msgcode = getattr(self.processor, "message_code_len", None)
        enc_ratio = getattr(self.processor, "encode_ratio", None)
        if msgcode is None or enc_ratio is None:
            return None
        try:
            return int(int(msgcode) * float(enc_ratio))
        except Exception:
            return None

    def _available_message_num(self, generated_len: int) -> Optional[int]:
        # upstream: available_message_num = generated_length // encode_len
        encode_len = self._encode_len()
        if encode_len is None or encode_len <= 0:
            return None
        return int(generated_len // encode_len)

    @staticmethod
    def _z_score(obs: float, exp: float, var: float) -> Optional[float]:
        if var <= 0.0:
            return None
        return float((obs - exp) / (var ** 0.5))

    # ----------------- zero-arg offline detector -----------------

    def detect_last(self) -> Dict[str, Any]:
        """
        Returns ONLY score-related fields (compact output).

        RANDOM:
          - decode only the generated completion segment
          - decode only the prefix that covers full encode_len blocks
          - outputs: bit_accuracy, exact_match, available_message_num

        PDA:
          - outputs: green_fraction, z_score, decision, counts
        """
        if self._cache_full_ids is None or self._cache_prefix_len is None:
            raise RuntimeError("No cached sequence for detection. Run generation with this processor first.")

        full_ids = self._cache_full_ids
        pre_len = int(self._cache_prefix_len)

        try:
            if self._mode == "random":
                # Match upstream: decode completion only
                generated_ids = full_ids[pre_len:]
                generated_len = int(generated_ids.numel())

                encode_len = self._encode_len()
                available = self._available_message_num(generated_len)

                # Acceleration: only keep the token prefix that can contribute to full blocks
                if available is not None and encode_len is not None and encode_len > 0:
                    need_tokens = int(available * encode_len)
                    generated_ids = generated_ids[:need_tokens]

                input_ids = generated_ids.unsqueeze(0)

                # Move to message_model device to avoid mismatch
                mm = getattr(self.processor, "message_model", None)
                if mm is not None and getattr(mm, "device", None) is not None:
                    target_dev = mm.device
                    try:
                        target_dev = torch.device(target_dev) if not isinstance(target_dev, torch.device) else target_dev
                    except Exception:
                        target_dev = mm.device
                    try:
                        input_ids = input_ids.to(target_dev, non_blocking=True)
                    except Exception:
                        pass

                decoded_message, _info = self.processor.decode_with_input_ids(input_ids, disable_tqdm=True)

                original = None
                if hasattr(self.processor, "message"):
                    try:
                        original = self.processor.message.detach().cpu().tolist()
                    except Exception:
                        original = None

                bit_accuracy = None
                exact_match = None
                if original is not None and available is not None:
                    # upstream compares prefixes of length `available`
                    dec = decoded_message[:available]
                    org = original[:available]
                    exact_match = (dec == org)
                    if available > 0:
                        # per-bit accuracy (score-related, compact)
                        correct = sum(int(a == b) for a, b in zip(dec, org))
                        bit_accuracy = float(correct / float(available))
                    else:
                        bit_accuracy = 0.0
                        exact_match = True

                out = {
                    "mode": "random",
                    "available_message_num": available,
                    "bit_accuracy": bit_accuracy,
                    "exact_match": exact_match,
                }

            elif self._mode == "pda":
                T = int(self._pda_T)
                G = int(self._pda_G)
                green_fraction = float(G) / float(T) if T > 0 else 0.0

                exp = float(self._pda_sum_p)
                var = float(self._pda_sum_var)
                z = self._z_score(float(G), exp, var)
                decision = (z is not None and z > float(self._z_threshold))

                out = {
                    "mode": "pda",
                    "num_tokens_scored": T,
                    "num_green_tokens": G,
                    "green_fraction": green_fraction,
                    "expected_num_green": exp,
                    "z_score": z,
                    "z_threshold": float(self._z_threshold),
                    "decision": decision,
                    "pda_hooked": bool(self._pda_hooked),
                }

            else:
                raise NotImplementedError(f"detect_last not implemented for mode {self._mode}")

        finally:
            # Clear caches to avoid accidental reuse
            self._cache_full_ids = None
            self._cache_prefix_len = None
            self._cache_prev_len = None

            # Reset PDA stats
            self._pda_prev_class = None
            self._pda_last_pred = None
            self._pda_T = 0
            self._pda_G = 0
            self._pda_sum_p = 0.0
            self._pda_sum_var = 0.0

        return out

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
        self._cache_full_ids = None
        self._cache_prefix_len = None
        self._cache_prev_len = None
        self._pda_prev_class = None
        self._pda_last_pred = None
        self._pda_T = 0
        self._pda_G = 0
        self._pda_sum_p = 0.0
        self._pda_sum_var = 0.0
