# generation.py

import copy
import threading
import time as _time
from typing import Any, Dict, List, Optional, Tuple

import torch
from transformers import LogitsProcessorList
from transformers.generation.stopping_criteria import StoppingCriteriaList, MaxLengthCriteria

from config import SAMPLING_MODE, ALLOW_GENERATOR_FALLBACK, RNG_SEED_FALLBACK
from runtime import model, tokenizer

def infer_input_device(model) -> torch.device:
    """
    Infer the correct input device for single-GPU or Transformers/Accelerate
    device_map="auto" multi-GPU dispatch.

    For sharded models, input_ids should be placed on the device that owns the
    embedding layer / first block. Accelerate dispatch hooks then move hidden
    states across GPUs according to model.hf_device_map.
    """
    hf_device_map = getattr(model, "hf_device_map", None)

    if isinstance(hf_device_map, dict) and hf_device_map:
        preferred_keys = (
            "model.embed_tokens",
            "transformer.wte",
            "gpt_neox.embed_in",
            "backbone.embed_tokens",
            "embed_tokens",
        )

        for key in preferred_keys:
            if key in hf_device_map:
                dev = hf_device_map[key]
                return torch.device(f"cuda:{dev}" if isinstance(dev, int) else dev)

        for dev in hf_device_map.values():
            if isinstance(dev, int):
                return torch.device(f"cuda:{dev}")
            if isinstance(dev, str) and dev.startswith("cuda"):
                return torch.device(dev)

    return next(model.parameters()).device

_GLOBAL_RNG_LOCK = threading.Lock()

def normalize_sampling_args(
    do_sample: bool,
    temperature: Optional[float],
    top_p: Optional[float],
    mode: str = SAMPLING_MODE,
) -> Tuple[bool, float, float]:
    """
    mode:
      - "lenient_openai": do_sample=True and temp<=0 -> temp=1e-4; do_sample=False -> temp=1.0, top_p=1.0
      - "map_to_greedy":  do_sample=True and temp<=0 -> do_sample=False (force greedy)
      - "strict":         do_sample=True and temp<=0 -> raise ValueError
    """
    if not do_sample:
        return False, 1.0, 1.0

    t = 1.0 if temperature is None else float(temperature)
    p = 1.0 if top_p is None else float(top_p)

    if t <= 0:
        if mode == "lenient_openai":
            t = 1e-4
        elif mode == "map_to_greedy":
            return False, 1.0, 1.0
        else:
            raise ValueError("temperature must be > 0 when do_sample=True")

    # Constrain top_p into (0, 1]
    if not (0 < p <= 1.0):
        p = 1.0

    return True, t, p

def pick_seed(rng_seed: Optional[int], input_ids: torch.LongTensor) -> Optional[int]:
    """
    Select seed used for this sampling call:
      - If rng_seed is provided -> use it
      - Else follow RNG_SEED_FALLBACK:
          * 'derived' -> derive a stable seed from prompt sum
          * otherwise -> return None (HF default behavior; no generator passed)
    """
    if rng_seed is not None:
        return int(rng_seed)
    if RNG_SEED_FALLBACK == "derived":
        return int(torch.sum(input_ids).item() % (2**31 - 1))
    return None

def model_ctx_limit() -> Optional[int]:
    """
    Infer model max context length in tokens across common config keys.
    If rope_scaling exists, estimate effective upper bound via scaling factor.
    Returns None if cannot be inferred reliably.
    """
    cfg = getattr(model, "config", None)
    if cfg is None:
        return None

    base = None
    for name in ("max_position_embeddings", "max_seq_len", "max_sequence_length", "n_positions", "seq_length"):
        v = getattr(cfg, name, None)
        if isinstance(v, int) and v > 0:
            base = int(v)
            break

    if base is None:
        v = getattr(cfg, "max_length", None)
        base = int(v) if isinstance(v, int) and v > 0 else None

    if base is None:
        return None

    # rope_scaling inference (if present)
    try:
        rs = getattr(cfg, "rope_scaling", None)
        if isinstance(rs, dict):
            factor = rs.get("factor") or rs.get("rope_factor")
            if factor:
                base = int(base * float(factor))
    except Exception:
        pass

    return base

def cap_max_new_tokens(prompt_len: int, want_new: Optional[int]) -> int:
    ctx = model_ctx_limit()
    safe = int(want_new or 0)
    return max(0, min(safe, (ctx - prompt_len) if isinstance(ctx, int) else safe))

def prep_inputs(messages: List[Dict[str, str]]) -> Dict[str, torch.Tensor]:
    chat_text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    return tokenizer([chat_text], return_tensors="pt")

def safe_get_logits_processor(gen_cfg, prompt_len: int) -> LogitsProcessorList:
    """Safely fetch HF logits processors; fallback to empty list for models lacking the private API."""
    try:
        return model._get_logits_processor(
            generation_config=gen_cfg,
            input_ids_seq_length=prompt_len,
            encoder_input_ids=None,
            prefix_allowed_tokens_fn=None,
            logits_processor=None,
        )
    except Exception:
        return LogitsProcessorList([])

def safe_get_stopping_criteria(gen_cfg) -> StoppingCriteriaList:
    """Safely fetch HF stopping criteria; fallback to empty list for models lacking the private API."""
    try:
        return model._get_stopping_criteria(gen_cfg, None)
    except Exception:
        return StoppingCriteriaList([])

def build_hf_components(
    prompt_len: int,
    do_sample: bool,
    temperature: Optional[float],
    top_p: Optional[float],
    max_new_tokens: int,
):
    """
    Reuse HF generation subcomponents:
    - hf_logits_processor: HF-built processors (repetition penalty, etc.)
    - stopping_criteria: HF stopping criteria + explicit MaxLengthCriteria(prompt_len+max_new_tokens)
    """
    gen_cfg = copy.deepcopy(model.generation_config)
    gen_cfg.do_sample = bool(do_sample)
    if temperature is not None:
        gen_cfg.temperature = float(temperature)
    if top_p is not None:
        gen_cfg.top_p = float(top_p)

    max_len = int(prompt_len + max_new_tokens) if max_new_tokens and max_new_tokens > 0 else int(prompt_len)

    hf_lp = safe_get_logits_processor(gen_cfg, prompt_len)
    stopping_criteria = safe_get_stopping_criteria(gen_cfg)

    # Ensure MaxLengthCriteria is present
    has_maxlen = any(isinstance(c, MaxLengthCriteria) for c in stopping_criteria)
    if not has_maxlen:
        stopping_criteria.append(MaxLengthCriteria(max_length=max_len))

    return gen_cfg, hf_lp, stopping_criteria

def count_new_and_reason(
    seqs: torch.LongTensor,
    prompt_len: int,
    capped: int,
    eos_ids: List[int],
    pad_id: Optional[int],
) -> Tuple[List[int], List[str]]:
    """
    Per-sample length accounting & finish_reason:
      - 'length': reached capped max_new_tokens
      - 'stop'  : ended before cap (EOS or other stopping criteria)
    """
    B, _ = seqs.shape
    new_lens, reasons = [], []
    for b in range(B):
        new_part = seqs[b, prompt_len:]
        new_len = None

        if eos_ids:
            eos_tensor = torch.tensor(eos_ids, device=new_part.device, dtype=new_part.dtype)
            eos_mask = torch.isin(new_part, eos_tensor)
            idx = torch.nonzero(eos_mask, as_tuple=False)
            if idx.numel() > 0:
                first_eos_pos = int(idx[0].item())
                new_len = first_eos_pos + 1

        if new_len is None:
            if pad_id is not None:
                new_len = int((new_part != pad_id).sum().item())
            else:
                new_len = int(new_part.numel())

        if capped > 0 and new_len >= capped:
            reason = "length"
        else:
            reason = "stop"

        new_lens.append(new_len)
        reasons.append(reason)

    return new_lens, reasons

def fmt_ms(sec: float) -> str:
    try:
        return f"{sec * 1000.0:.3f}ms"
    except Exception:
        return f"{sec}s"

@torch.inference_mode()
def hf_generate_single(
    inputs: Dict[str, torch.Tensor],
    logits_processors: Optional[LogitsProcessorList],
    temperature: float,
    top_p: float,
    max_new_tokens: int,
    do_sample: bool,
    rng_seed: Optional[int],
) -> Tuple[str, int, int, int, str, float]:
    """
    Single-path generation wrapper returning:
      (text, prompt_tokens, completion_tokens, total_tokens, finish_reason, gen_elapsed_seconds)
    """
    device = infer_input_device(model)
    input_ids = inputs["input_ids"].to(device)
    attn = inputs.get("attention_mask", None)
    if attn is None:
        attn = torch.ones_like(input_ids, dtype=torch.long, device=device)
    else:
        attn = attn.to(device=device, dtype=torch.long)

    prompt_len = int(input_ids.shape[1])
    capped = cap_max_new_tokens(prompt_len, int(max_new_tokens or 0))

    if capped <= 0:
        reason = "length" if int(max_new_tokens or 0) > 0 else "stop"
        return "", prompt_len, 0, prompt_len, reason, 0.0

    do_sample, temperature, top_p = normalize_sampling_args(do_sample, temperature, top_p)
    _, hf_lp, stopping_criteria = build_hf_components(prompt_len, do_sample, temperature, top_p, capped)
    final_lp = LogitsProcessorList(list(hf_lp) + list(logits_processors or []))

    # Private generator path for deterministic sampling (recommended)
    seed_to_use = pick_seed(rng_seed, input_ids) if do_sample else None
    gen = None
    if do_sample and seed_to_use is not None:
        gen = torch.Generator(device=input_ids.device)
        gen.manual_seed(seed_to_use)

    def _call_generate(gen_arg):
        return model.generate(
            input_ids=input_ids,
            attention_mask=attn,
            do_sample=do_sample,
            temperature=temperature,
            top_p=top_p,
            max_new_tokens=capped,
            logits_processor=final_lp,
            stopping_criteria=stopping_criteria,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=model.generation_config.eos_token_id,
            generator=gen_arg,
            return_dict_in_generate=True,
        )

    t0 = _time.perf_counter()
    try:
        out = _call_generate(gen)
    except Exception as e:
        msg = str(e)
        need_fallback = (
            ALLOW_GENERATOR_FALLBACK
            and do_sample
            and seed_to_use is not None
            and ("not used by the model" in msg)
            and ("generator" in msg)
        )
        if not need_fallback:
            raise

        print("[server] generator not accepted by model; falling back to global RNG seeding")
        with _GLOBAL_RNG_LOCK:
            try:
                torch.manual_seed(seed_to_use)
                if torch.cuda.is_available():
                    torch.cuda.manual_seed_all(seed_to_use)
            except Exception:
                pass
            out = _call_generate(None)
    t1 = _time.perf_counter()

    seqs = out.sequences
    eos = model.generation_config.eos_token_id
    eos_ids = [eos] if isinstance(eos, int) else [int(x) for x in (eos or [])]

    new_lens, reasons = count_new_and_reason(seqs, prompt_len, capped, eos_ids, tokenizer.pad_token_id)
    text = tokenizer.batch_decode(seqs[:, prompt_len:], skip_special_tokens=True)[0]
    comp = new_lens[0]
    total = prompt_len + comp

    return text, prompt_len, comp, total, reasons[0], float(t1 - t0)
