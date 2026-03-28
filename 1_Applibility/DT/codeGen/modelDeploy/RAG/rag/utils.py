# -*- coding: utf-8 -*-
# pip install transformers accelerate torch
from __future__ import annotations
from typing import Callable, List, Dict, Optional, Protocol, Any
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from transformers.generation.logits_process import LogitsProcessor, LogitsProcessorList

########################################################
# 1) Retriever interface and adapter
########################################################

class RetrievalHit(Dict[str, Any]):
    """
    Expected fields (must include at least reference). You can extend it with more metadata.
      - reference: str      # Retrieved reference code text
      - score: float        # Optional retrieval score
      - task_id / task_name / prompt / prefix ... any of these may also appear
    """
    pass

class Retriever(Protocol):
    def retrieve(self, query: str, top_k: int = 1) -> List[RetrievalHit]: ...

class FunctionRetriever:
    """
    Adapt your existing function into a Retriever:
    the expected function signature is: fn(query_text: str, top_k: int) -> List[Dict]
    and the returned Dict must include 'reference'.
    """
    def __init__(self, fn: Callable[[str, int], List[Dict]]):
        self.fn = fn
    def retrieve(self, query: str, top_k: int = 1) -> List[RetrievalHit]:
        hits = self.fn(query, top_k)
        if not hits:
            return []
        if "reference" not in hits[0]:
            raise ValueError("retriever result is missing the 'reference' field")
        return hits  # type: ignore


########################################################
# 2) Soft-constraint processors (can be stacked with a watermark processor)
########################################################

# class ReferenceMarginEnforcer(LogitsProcessor):
#     """
#     Adaptive soft constraint:
#       At each step, add the minimum necessary bias to the next reference token
#       so it becomes the argmax, without masking other tokens.
#       finish_with_eos=True: force EOS in one step after copying completes.
#     Suitable for chaining with a Watermark Processor; place it at the end of
#     the chain as a final safeguard to ensure consistency.
#     """
#     def __init__(
#         self,
#         ref_ids: List[int],
#         start_len: int,
#         eos_token_id: int,
#         margin: float = 2.0,
#         finish_with_eos: bool = True,
#         max_bias: float = 50.0,
#     ):
#         self.ref_ids = [int(t) for t in ref_ids]
#         self.start_len = int(start_len)
#         self.eos_token_id = int(eos_token_id)
#         self.margin = float(margin)
#         self.finish_with_eos = bool(finish_with_eos)
#         self.max_bias = float(max_bias)

#     def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor) -> torch.FloatTensor:
#         step = input_ids.shape[-1] - self.start_len
#         if step < len(self.ref_ids):
#             tgt = self.ref_ids[step]
#             tgt_score = scores[:, tgt:tgt+1]
#             tmp = scores.clone()
#             tmp[:, tgt] = float("-inf")
#             max_others = tmp.max(dim=-1, keepdim=True).values
#             need = torch.clamp(max_others - tgt_score + self.margin, min=0.0, max=self.max_bias)
#             scores[:, tgt] += need.squeeze(-1)
#         elif self.finish_with_eos:
#             scores[:] = float("-inf")
#             scores[:, self.eos_token_id] = 0.0
#         return scores

# class ReferenceMarginEnforcer(LogitsProcessor):
#     """
#     Adaptive soft constraint: use progressive constraints and dynamic
#     reference adjustment to keep generated code as close as possible to the
#     reference code.
#     At the same time, simulate more realistic inference through logit
#     smoothing (temperature scaling) and diversity enhancements
#     (beam search, top-k).
#     """
#     def __init__(
#         self,
#         ref_ids: List[int],
#         start_len: int,
#         eos_token_id: int,
#         max_margin: float = 2.0,
#         min_margin: float = 2.0,
#         decay_rate: float = 0.95,
#         temperature: float = 0.3,
#         max_bias: float = 50.0,
#         window_size: int = 100,
#         finish_with_eos: bool = True,
#     ):
#         """
#         Initialize ReferenceMarginEnforcer with soft-constraint and related
#         parameters:
#         Parameters:
#         - ref_ids: token IDs of the reference code.
#         - start_len: token length of the input prefix.
#         - eos_token_id: the ID of the EOS token.
#         - max_margin: maximum margin controlling the strength of the
#           reference bias.
#         - min_margin: minimum margin to avoid margins becoming too small.
#         - decay_rate: the rate at which the margin decays over steps.
#         - temperature: controls the smoothness of logits.
#         - max_bias: maximum bias to prevent excessive biasing.
#         - finish_with_eos: whether to force EOS when generation ends.
#         - window_size: size of the dynamic reference window, controlling how
#           frequently the reference sequence is updated.
#         """
#         self.ref_ids = ref_ids
#         self.start_len = start_len
#         self.eos_token_id = eos_token_id
#         self.max_margin = max_margin
#         self.min_margin = min_margin
#         self.decay_rate = decay_rate
#         self.temperature = temperature
#         self.max_bias = max_bias
#         self.window_size = window_size
#         self.finish_with_eos = finish_with_eos

#     def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor) -> torch.FloatTensor:
#         step = input_ids.shape[-1] - self.start_len

#         # Dynamically compute the margin: decay it as generation progresses.
#         margin = max(self.min_margin, self.max_margin * (self.decay_rate ** step))

#         # Compute the score of the reference token; the goal is to make it
#         # the argmax.
#         if step < len(self.ref_ids):
#             tgt = self.ref_ids[step]
#             tgt_score = scores[:, tgt:tgt+1]

#             # Compute the maximum score among the other tokens.
#             tmp = scores.clone()
#             tmp[:, tgt] = float("-inf")
#             max_others = tmp.max(dim=-1, keepdim=True).values
#             need = torch.clamp(max_others - tgt_score + margin, min=0.0, max=self.max_bias)
#             scores[:, tgt] += need.squeeze(-1)

#         # Dynamic reference adjustment: allow the reference sequence to update
#         # during generation.
#         reference_window = self.ref_ids[max(0, step - self.window_size):step]
#         for ref_token in reference_window:
#             scores[:, ref_token] += 1.0  # Increase the reference token score

#         # If the reference content has been fully generated, force EOS.
#         if step >= len(self.ref_ids) and self.finish_with_eos:
#             scores[:] = float("-inf")
#             scores[:, self.eos_token_id] = 0.0

#         # Smooth the logits distribution by temperature scaling to increase
#         # diversity.
#         scores = scores / self.temperature

#         return scores

class HybridKLProjectionEnforcer(LogitsProcessor):
    """
    Support both 'margin' and 'prob' constraints and transition smoothly through lambda in [0,1]:
      - lambda=0: margin-only constraint s_t' - max_{j!=t} s_j' >= gamma (more stable for hard copying)
      - lambda=1: probability-only constraint q_t(delta) = alpha (minimum KL lift to reach the target probability)
      - 0<lambda<1: satisfy both weakened margin gamma_lambda and strengthened probability alpha_lambda
    Optionally, ensure_copy=True provides a tiny safety margin to guarantee strict copying under greedy decoding.
    """
    def __init__(
        self,
        ref_ids: List[int],
        start_len: int,
        eos_token_id: int,
        # Target parameters
        gamma: float = 2.5,       # Target logit margin in pure-margin mode
        alpha: float = 0.5,       # Target probability in pure-prob mode
        # Mixing and scheduling:
        # lambda=0: pure logit copying; lambda=1: pure probability boosting
        lambda_start: float = 0.0,
        lambda_end: float = 1.0,
        schedule: str = "linear",   # "constant" | "linear" (step-wise interpolation from start to end)
        # Numerical stability and safety
        max_bias: float = 50.0,
        eps: float = 1e-12,
        compute_in_fp32: bool = False,
        finish_with_eos: bool = True,
        ensure_copy: bool = False,      # Fallback safeguard to enforce copying
        gamma_safe: float = 1e-6,       # Tiny fallback margin
    ):
        self.ref_ids = [int(t) for t in ref_ids]
        self.start_len = int(start_len)
        self.eos_token_id = int(eos_token_id)
        # Targets
        self.gamma = float(gamma)
        self.alpha = float(alpha)
        # Mixing schedule
        self.lambda_start = float(lambda_start)
        self.lambda_end = float(lambda_end)
        assert 0.0 <= self.lambda_start <= 1.0 and 0.0 <= self.lambda_end <= 1.0
        assert schedule in ("constant", "linear")
        self.schedule = schedule
        # Numerical settings
        self.max_bias = float(max_bias)
        self.eps = float(eps)
        self.compute_in_fp32 = bool(compute_in_fp32)
        self.finish_with_eos = bool(finish_with_eos)
        # Copy fallback
        self.ensure_copy = bool(ensure_copy)
        self.gamma_safe = float(gamma_safe)

    def _lambda_at(self, step: int, total_steps: int) -> float:
        if self.schedule == "constant" or total_steps <= 1:
            return self.lambda_end  # Constant
        # Linearly interpolate from start -> end
        ratio = step / (total_steps - 1)
        return self.lambda_start + (self.lambda_end - self.lambda_start) * ratio

    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor) -> torch.FloatTensor:
        step = input_ids.shape[-1] - self.start_len
        L = len(self.ref_ids)

        if step < L:
            t = self.ref_ids[step]
            # 1) Mixing coefficient lambda at the current step
            lam = self._lambda_at(step, L)  # in [0,1]

            # 2) Weakened margin target: gamma_lambda = (1-lambda)*gamma
            gamma_eff = (1.0 - lam) * self.gamma

            # 3) Strengthened probability target: alpha_lambda = (1-lambda)*p_t + lambda*alpha
            #    First compute the current p_t (prefer logsumexp in FP32)
            scores = torch.clamp(scores, min=-1e5, max=1e5)
            if self.compute_in_fp32 and scores.dtype != torch.float32:
                scores_f = scores.float()
            else:
                scores_f = scores
            logZ = torch.logsumexp(scores_f, dim=-1, keepdim=True)  # Bx1
            log_p_t = scores_f[:, t:t+1] - logZ                     # Bx1
            p_t = log_p_t.exp().clamp(self.eps, 1.0 - self.eps)     # Bx1
            alpha_eff = ((1.0 - lam) * p_t) + (lam * self.alpha)
            alpha_eff = alpha_eff.clamp(self.eps, 1.0 - self.eps)   # Bx1

            # 4) Compute the minimum lift required by each constraint
            #   margin: delta_m = max(0, gamma_lambda - (s_t - m))
            tmp = scores.clone()
            tmp[:, t] = float("-inf")
            max_others = tmp.max(dim=-1, keepdim=True).values  # Bx1
            delta_m = (max_others - scores[:, t:t+1] + gamma_eff).clamp_min(0.0)

            #   prob: delta_p = log(alpha_eff(1-p) / (p(1-alpha_eff))); clamp to zero if negative
            delta_p = torch.log(alpha_eff * (1.0 - p_t) / (p_t * (1.0 - alpha_eff)))
            delta_p = delta_p.clamp_min(0.0)

            # 5) Satisfy both constraints by taking the maximum, then clamp by max_bias
            need = torch.maximum(delta_m, delta_p).clamp_max(self.max_bias)

            # 6) Optional fallback: ensure greedy copying with a tiny hard margin
            if self.ensure_copy:
                delta_safe = (max_others - scores[:, t:t+1] + self.gamma_safe).clamp_min(0.0)
                need = torch.maximum(need, delta_safe)

            scores[:, t] += need.squeeze(-1)

        elif self.finish_with_eos:
            scores[:] = float("-inf")
            scores[:, self.eos_token_id] = 0.0

        return scores

# class HybridKLProjectionEnforcer(LogitsProcessor):
#     """
#     Support both 'margin' and 'prob' constraints and transition smoothly
#     through λ∈[0,1]:
#       - λ=0: margin-only constraint s_t' - max_{j≠t} s_j' ≥ γ
#         (more stable for hard copying)
#       - λ=1: probability-only constraint q_t(δ) > max(p_others)
#         (target probability is slightly larger than other tokens)
#       - 0<λ<1: satisfy both weakened margin γ_λ and strengthened
#         probability α_λ
#     Optionally, ensure_copy=True provides a tiny safety margin fallback to
#     guarantee strict greedy copying.
#     """
#     def __init__(
#         self,
#         ref_ids: List[int],
#         start_len: int,
#         eos_token_id: int,
#         # Target parameters
#         gamma: float = 2.0,       # Target logit margin in pure-margin mode
#         # Revised: use an increment to ensure the target token probability is
#         # larger than the current maximum probability by a fixed amount
#         alpha: float = 0.1,  # Increment above the current maximum probability
#         # Mixing and scheduling:
#         lambda_start: float = 0.0,
#         lambda_end: float = 1.0,
#         schedule: str = "linear",   # "constant" | "linear" (step-wise start→end)
#         # Numerical stability and safety
#         max_bias: float = 50.0,
#         eps: float = 1e-12,
#         compute_in_fp32: bool = False,
#         finish_with_eos: bool = True,
#         ensure_copy: bool = False,      # Fallback to guarantee copying
#         gamma_safe: float = 1e-6,       # Tiny fallback margin
#     ):
#         self.ref_ids = [int(t) for t in ref_ids]
#         self.start_len = int(start_len)
#         self.eos_token_id = int(eos_token_id)
#         # Targets
#         self.gamma = float(gamma)
#         self.alpha = float(alpha)
#         # Mixing schedule
#         self.lambda_start = float(lambda_start)
#         self.lambda_end = float(lambda_end)
#         assert 0.0 <= self.lambda_start <= 1.0 and 0.0 <= self.lambda_end <= 1.0
#         assert schedule in ("constant", "linear")
#         self.schedule = schedule
#         # Numerical settings
#         self.max_bias = float(max_bias)
#         self.eps = float(eps)
#         self.compute_in_fp32 = bool(compute_in_fp32)
#         self.finish_with_eos = bool(finish_with_eos)
#         # Copy fallback
#         self.ensure_copy = bool(ensure_copy)
#         self.gamma_safe = float(gamma_safe)

#     def _lambda_at(self, step: int, total_steps: int) -> float:
#         if self.schedule == "constant" or total_steps <= 1:
#             return self.lambda_end  # Constant
#         # Linear interpolation from start -> end
#         ratio = step / (total_steps - 1)
#         return self.lambda_start + (self.lambda_end - self.lambda_start) * ratio

#     def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor) -> torch.FloatTensor:
#         step = input_ids.shape[-1] - self.start_len
#         L = len(self.ref_ids)

#         if step < L:
#             t = self.ref_ids[step]
#             # 1) Mixing coefficient λ at the current step
#             lam = self._lambda_at(step, L)  # in [0,1]

#             # 2) Weakened margin target: γ_λ = (1-λ)*γ
#             gamma_eff = (1.0 - lam) * self.gamma

#             # 3) Probability target: the target token probability exceeds the
#             # current maximum probability by a fixed increment
#             if self.compute_in_fp32 and scores.dtype != torch.float32:
#                 scores_f = scores.float()
#             else:
#                 scores_f = scores

#             logZ = torch.logsumexp(scores_f, dim=-1, keepdim=True)  # Bx1
#             raw_probs = torch.softmax(scores_f, dim=-1)  # BxV
#             max_other_probs, _ = raw_probs.max(dim=-1, keepdim=True)  # Bx1: max probability

#             # Set the target token probability slightly above the current
#             # maximum probability.
#             target_prob = max_other_probs + self.alpha
#             target_prob = target_prob.clamp(self.eps, 1.0 - self.eps)  # Keep within [0, 1]

#             # Compute the required logit offset for the target token.
#             log_target_prob = target_prob.log()
#             delta_p = log_target_prob - scores_f[:, t:t+1]

#             # 4) Compute the margin constraint: δ_m = max(0, γ_λ - (s_t - m))
#             tmp = scores.clone()
#             tmp[:, t] = float("-inf")
#             max_others = tmp.max(dim=-1, keepdim=True).values  # Bx1
#             delta_m = (max_others - scores[:, t:t+1] + gamma_eff).clamp_min(0.0)

#             # 5) Satisfy both constraints by taking the maximum, then clamp by
#             # max_bias.
#             need = torch.maximum(delta_m, delta_p).clamp_max(self.max_bias)

#             # 6) Optional fallback: ensure greedy copying with a tiny hard
#             # margin.
#             if self.ensure_copy:
#                 delta_safe = (max_others - scores[:, t:t+1] + self.gamma_safe).clamp_min(0.0)
#                 need = torch.maximum(need, delta_safe)

#             scores[:, t] += need.squeeze(-1)

#         elif self.finish_with_eos:
#             scores[:] = float("-inf")
#             scores[:, self.eos_token_id] = 0.0

#         return scores


class ReferenceBias(LogitsProcessor):
    """
    Fixed-bias soft constraint: add +bias to the next reference token without masking other tokens.
    A bias of 12~20 often reaches 99%+ consistency and is simpler than the margin-based version.
    """
    def __init__(self, ref_ids, start_len, eos_token_id, bias=12.0, finish_with_eos=True):
        self.ref_ids = [int(t) for t in ref_ids]
        self.start_len = int(start_len)
        self.eos_token_id = int(eos_token_id)
        self.bias = float(bias)
        self.finish_with_eos = bool(finish_with_eos)
    def __call__(self, input_ids, scores):
        step = input_ids.shape[-1] - self.start_len
        if step < len(self.ref_ids):
            scores[:, self.ref_ids[step]] += self.bias
        elif self.finish_with_eos:
            scores[:] = float("-inf")
            scores[:, self.eos_token_id] = 0.0
        return scores

class HardClampToReference(LogitsProcessor):
    """
    Hard clamping (optional): allow only the next reference token at each step, and only eos after copying finishes.
    This is for extreme cases requiring 100% consistency; when combined with a watermark processor, place it last in the processor chain.
    """
    def __init__(self, ref_ids, start_len, eos_token_id):
        self.ref_ids = [int(t) for t in ref_ids]
        self.start_len = int(start_len)
        self.eos_token_id = int(eos_token_id)
    def __call__(self, input_ids, scores):
        step = input_ids.shape[-1] - self.start_len
        scores[:] = float("-inf")
        if step < len(self.ref_ids):
            scores[:, self.ref_ids[step]] = 0.0
        else:
            scores[:, self.eos_token_id] = 0.0
        return scores


########################################################
# 3) HuggingFace model engine (generic, can be replaced with any CausalLM)
########################################################

class HFModelEngine:
    """
    Unified wrapper around a HuggingFace CausalLM:
      - Automatically handles pad_token / attention_mask
      - Single GPU is the safest (device_map=None); when sharding with device_map="auto", inputs are automatically moved to the embedding-layer device
      - Provides a deterministic generate interface with logits_processor support
    """
    def __init__(
        self,
        model_name: str,
        device: Optional[str] = None,
        fp16: bool = True,
        device_map: Optional[str] = None,   # None: single GPU; "auto": sharded
        revision: Optional[str] = None,
        trust_remote_code: bool = True,
        use_auth_token: bool = True,
        max_context: int = 8192,
    ):
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name, 
            revision=revision,
            trust_remote_code=trust_remote_code,
            use_auth_token=use_auth_token,
            truncation_side="left",
            padding_side="right",
        )
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        torch_dtype = torch.float16 if (fp16 and device == "cuda") else torch.float32

        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch_dtype,
            device_map=device_map,              # It is recommended to start with None
            trust_remote_code=trust_remote_code,
        )
        # Target device for model inputs
        if hasattr(self.model, "hf_device_map") and device_map == "auto":
            wte_dev = self.model.hf_device_map.get("transformer.wte")
            self.input_device = torch.device(wte_dev if wte_dev is not None else list(self.model.hf_device_map.values())[0])
        else:
            self.model.to(device)
            self.input_device = next(self.model.parameters()).device

        self.max_context = max_context

    def tokenize_to_device(self, text: str):
        tok = self.tokenizer(text, return_tensors="pt", add_special_tokens=True)
        input_ids = tok["input_ids"].to(self.input_device)
        attention_mask = tok.get("attention_mask", torch.ones_like(input_ids)).to(self.input_device)
        return input_ids, attention_mask

    def ids_from_text(self, text: str) -> List[int]:
        return self.tokenizer(text, add_special_tokens=False, return_tensors="pt").input_ids[0].tolist()

    def generate_with_processors(
        self,
        input_ids: torch.LongTensor,
        attention_mask: torch.LongTensor,
        processors: LogitsProcessorList,
        max_new_tokens: int,
        eos_token_id: Optional[int] = None,
        pad_token_id: Optional[int] = None,
    ) -> torch.LongTensor:
        if eos_token_id is None:
            eos_token_id = self.tokenizer.eos_token_id
        if pad_token_id is None:
            pad_token_id = self.tokenizer.pad_token_id

        out = self.model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            max_new_tokens=max_new_tokens,  # Maximum number of generated tokens
            do_sample=True,                 # Enable sampling
            temperature=0.2,                # Set temperature
            top_p=0.95,                     # Use top-p (nucleus sampling)
            num_beams=1,                    # Use greedy/one-beam decoding
            use_cache=True,                 # Enable cache
            eos_token_id=eos_token_id,      # End-of-sequence token id
            pad_token_id=pad_token_id,      # Padding token id
            logits_processor=processors     # Apply logits processors as constraints
        )
        return out


########################################################
# 4) RAG orchestration: retrieval + soft constraint / hard clamp + optional watermark
########################################################

class RagConstrainedGenerator:
    """
    Orchestrator with a retriever and an HF model engine:
      1) Use retriever(query) to recall a reference
      2) Build a soft-constraint or hard-clamp LogitsProcessor (optionally stacked with watermark_processor)
      3) Call the HF engine generate method
    """
    def __init__(self, engine: HFModelEngine, retriever: Retriever):
        self.engine = engine
        self.retriever = retriever

    def _check_context(self, start_len: int, ref_len: int):
        total = start_len + ref_len + 1  # +1 for EOS
        if total > self.engine.max_context:
            raise ValueError(f"Context limit exceeded: input({start_len}) + gen({ref_len}+1) = {total} > {self.engine.max_context}")

    def generate(
        self,
        prompt: str,
        prefix: str,
        top_k: int = 1,
        constraint: str = "adaptive",    # 'adaptive' | 'fixed' | 'hard'
        gamma: float = 2.5,
        alpha: float = 0.1,
        lambda_start: float = 0.0,
        lambda_end: float = 1.0,
        schedule: str = "linear",   # "constant" | "linear"
        max_bias: float = 50.0,
        eps: float = 1e-12,
        compute_in_fp32: bool = False,
        finish_with_eos: bool = True,
        ensure_copy: bool = False,
        gamma_safe: float = 1e-6,
        fixed_bias: float = 12.0,
        watermark_processor: Optional[LogitsProcessor] = None,
        system_prompt: str = "Output exactly the following code. Begin now.\n",
    ) -> Dict[str, Any]:
        # 1) RAG retrieval
        hits = self.retriever.retrieve((prompt or "") + "\n" + (prefix or ""), top_k=top_k)
        if not hits:
            raise RuntimeError("RAG did not retrieve any reference code.")
        best = hits[0]
        ref_text = best["reference"]

        # 2) Prepare the input
        input_ids, attention_mask = self.engine.tokenize_to_device(system_prompt)
        start_len = input_ids.shape[-1]
        ref_ids = self.engine.ids_from_text(ref_text)
        self._check_context(start_len, len(ref_ids))

        # 3) Processor chain (order: constraint -> watermark)
        processors = LogitsProcessorList()

        # Select the constraint strategy based on the constraint type
        if constraint == "adaptive":
            processors.append(HybridKLProjectionEnforcer(
                ref_ids=ref_ids,
                start_len=start_len,
                eos_token_id=self.engine.tokenizer.eos_token_id,
                gamma=gamma,
                alpha=alpha,
                lambda_start=lambda_start,
                lambda_end=lambda_end,
                schedule=schedule,
                max_bias=max_bias,
                eps=eps,
                compute_in_fp32=compute_in_fp32,
                finish_with_eos=finish_with_eos,
                ensure_copy=ensure_copy,
                gamma_safe=gamma_safe,
            ))
        elif constraint == "fixed":
            processors.append(ReferenceBias(
                ref_ids=ref_ids,
                start_len=start_len,
                eos_token_id=self.engine.tokenizer.eos_token_id,
                bias=fixed_bias,
                finish_with_eos=finish_with_eos
            ))
        elif constraint == "hard":
            processors.append(HardClampToReference(
                ref_ids=ref_ids,
                start_len=start_len,
                eos_token_id=self.engine.tokenizer.eos_token_id
            ))
        else:
            raise ValueError("constraint must be one of 'adaptive' | 'fixed' | 'hard'")
        
        if watermark_processor is not None:
            processors.append(watermark_processor)

        # 4) Decoding: pass the processor chain and generation parameters
        out = self.engine.generate_with_processors(
            input_ids=input_ids,
            attention_mask=attention_mask,
            processors=processors,
            max_new_tokens=len(ref_ids) + 1
        )
        gen_ids = out[0][start_len:]
        text = self.engine.tokenizer.decode(gen_ids, skip_special_tokens=True)

        exact_match = (text == ref_text) or text.endswith(ref_text)
        return {
            # "text": ref_text if not exact_match else text,  # Safe fallback
            "text": text,
            "exact_match": bool(exact_match),
            "ref_len_tokens": len(ref_ids),
            "route": f"rag+{constraint}",
            "rag_meta": best
        }
