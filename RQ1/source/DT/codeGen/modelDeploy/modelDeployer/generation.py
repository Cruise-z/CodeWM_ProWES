# generation.py

from dataclasses import dataclass
import threading
import time as _time
from typing import Any, Dict, List, Optional, Sequence, Tuple

import torch
from transformers import LogitsProcessorList, StoppingCriteria, StoppingCriteriaList
from transformers.generation.logits_process import (
    TemperatureLogitsWarper,
    TopKLogitsWarper,
    TopPLogitsWarper,
)

from config import SAMPLING_MODE, ALLOW_GENERATOR_FALLBACK, RNG_SEED_FALLBACK
from processors import WatermarkPlacement
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


@dataclass(frozen=True)
class SamplingPlan:
    logits_processors: Optional[LogitsProcessorList]
    host_temperature: float
    host_top_p: float
    host_top_k: Optional[int]
    has_post_topp: bool
    execution_backend: str = "legacy_native"
    decode_graph_nodes: tuple[str, ...] = ()

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


def _ensure_post_topp_host_warpers_supported() -> None:
    config = model.generation_config
    active = []
    checks = {
        "top_h": lambda value: value is not None,
        "min_p": lambda value: value is not None,
        "typical_p": lambda value: value is not None and float(value) < 1.0,
        "epsilon_cutoff": lambda value: value is not None and 0.0 < float(value) < 1.0,
        "eta_cutoff": lambda value: value is not None and 0.0 < float(value) < 1.0,
        "watermarking_config": lambda value: value is not None,
        "renormalize_logits": bool,
    }
    for name, is_active in checks.items():
        value = getattr(config, name, None)
        if is_active(value):
            active.append(f"{name}={value!r}")
    if active:
        raise ValueError(
            "POST_TOPP placement does not support additional host warpers after "
            f"the explicit TopP boundary: {', '.join(active)}"
        )


def _min_tokens_to_keep() -> int:
    num_beams = int(getattr(model.generation_config, "num_beams", 1) or 1)
    if num_beams <= 1:
        return 1
    eos = model.generation_config.eos_token_id
    eos_count = 1 if isinstance(eos, int) else len(eos or [])
    return eos_count + 1


_DECODE_HOST_PROCESSORS = "host.processors"
_DECODE_TEMPERATURE = "sampling.temperature"
_DECODE_TOP_K = "sampling.top_k"
_DECODE_TOP_P = "sampling.top_p"
_DECODE_SAMPLER = "sampling.sampler"
_DECODE_ANCHORS = (
    _DECODE_HOST_PROCESSORS,
    _DECODE_TEMPERATURE,
    _DECODE_TOP_K,
    _DECODE_TOP_P,
    _DECODE_SAMPLER,
)


def _normalize_order_mapping(value: Any) -> dict[str, tuple[str, ...]]:
    if not isinstance(value, dict):
        raise ValueError(f"processor decode order must be a mapping, got {type(value)}")
    after = value.get("after") or ()
    before = value.get("before") or ()
    if isinstance(after, str):
        after = (after,)
    if isinstance(before, str):
        before = (before,)
    normalized = {
        "after": tuple(str(item).strip() for item in after),
        "before": tuple(str(item).strip() for item in before),
    }
    if not normalized["after"] or not normalized["before"]:
        raise ValueError("processor decode order requires after and before constraints")
    return normalized


def _processor_node_id(processor: Any, index: int) -> str:
    method = str(getattr(processor, "_codewm_method", "external")).strip().lower()
    component = str(getattr(processor, "_codewm_component", index)).strip().lower()
    return f"method.{method}.{component}"


def _topological_sampling_nodes(
    processors: Sequence[Any],
    *,
    do_sample: bool,
    temperature: float,
    top_p: float,
) -> tuple[list[Any], bool, bool, tuple[str, ...]]:
    """Compose method-declared relative constraints with host sampling nodes."""
    payloads: dict[str, Any] = {
        _DECODE_HOST_PROCESSORS: None,
        _DECODE_TEMPERATURE: None,
        _DECODE_TOP_K: None,
        _DECODE_TOP_P: None,
        _DECODE_SAMPLER: None,
    }
    edges: dict[str, set[str]] = {name: set() for name in _DECODE_ANCHORS}
    indegree: dict[str, int] = {name: 0 for name in _DECODE_ANCHORS}
    sort_keys: dict[str, tuple[int, int]] = {
        name: (rank * 1000, 0) for rank, name in enumerate(_DECODE_ANCHORS)
    }

    def add_node(name: str, payload: Any, sort_key: tuple[int, int]) -> None:
        if name in payloads:
            raise ValueError(f"duplicate decode graph node: {name}")
        payloads[name] = payload
        edges[name] = set()
        indegree[name] = 0
        sort_keys[name] = sort_key

    def add_edge(source: str, target: str) -> None:
        if source not in payloads:
            raise ValueError(f"unknown decode-order dependency: {source}")
        if target not in payloads:
            raise ValueError(f"unknown decode-order dependency: {target}")
        if target not in edges[source]:
            edges[source].add(target)
            indegree[target] += 1

    for source, target in zip(_DECODE_ANCHORS, _DECODE_ANCHORS[1:]):
        add_edge(source, target)

    declarations: list[tuple[str, dict[str, tuple[str, ...]]]] = []
    for index, processor in enumerate(processors):
        node_id = _processor_node_id(processor, index)
        processor._codewm_decode_node = node_id
        add_node(node_id, processor, (500, index))
        raw_order = getattr(processor, "_codewm_decode_order", None)
        if raw_order is not None:
            order = _normalize_order_mapping(raw_order)
        else:
            placement = WatermarkPlacement(getattr(processor, "_codewm_placement"))
            if placement is WatermarkPlacement.PRE_WARPER:
                order = {
                    "after": (_DECODE_HOST_PROCESSORS,),
                    "before": (_DECODE_TEMPERATURE,),
                }
            elif placement is WatermarkPlacement.POST_TOPP:
                order = {
                    "after": (_DECODE_TOP_P,),
                    "before": (_DECODE_SAMPLER,),
                }
            else:
                raise ValueError(f"unsupported watermark placement: {placement!r}")
        declarations.append((node_id, order))

    for node_id, order in declarations:
        for source in order["after"]:
            add_edge(source, node_id)
        for target in order["before"]:
            add_edge(node_id, target)

    ready = sorted(
        (name for name, count in indegree.items() if count == 0),
        key=sort_keys.__getitem__,
    )
    ordered_names: list[str] = []
    while ready:
        current = ready.pop(0)
        ordered_names.append(current)
        for target in sorted(edges[current], key=sort_keys.__getitem__):
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
                ready.sort(key=sort_keys.__getitem__)
    if len(ordered_names) != len(payloads):
        blocked = sorted(name for name, count in indegree.items() if count > 0)
        raise ValueError(f"cyclic or unsatisfied decode-order constraints: {blocked}")

    top_p_index = ordered_names.index(_DECODE_TOP_P)
    sampler_index = ordered_names.index(_DECODE_SAMPLER)
    has_post_topp = any(
        top_p_index < ordered_names.index(node_id) < sampler_index
        for node_id, _ in declarations
    )
    external_node_ids = [node_id for node_id, _ in declarations]
    native_pre_warper = ordered_names == [
        _DECODE_HOST_PROCESSORS,
        *external_node_ids,
        _DECODE_TEMPERATURE,
        _DECODE_TOP_K,
        _DECODE_TOP_P,
        _DECODE_SAMPLER,
    ]

    if not native_pre_warper:
        _ensure_post_topp_host_warpers_supported()
        min_tokens_to_keep = _min_tokens_to_keep()
        top_k = int(getattr(model.generation_config, "top_k", 0) or 0)
        if do_sample and temperature != 1.0:
            payloads[_DECODE_TEMPERATURE] = TemperatureLogitsWarper(
                float(temperature)
            )
        if do_sample and top_k != 0:
            payloads[_DECODE_TOP_K] = TopKLogitsWarper(
                top_k=top_k,
                min_tokens_to_keep=min_tokens_to_keep,
            )
        if do_sample and top_p < 1.0:
            payloads[_DECODE_TOP_P] = TopPLogitsWarper(
                top_p=float(top_p),
                min_tokens_to_keep=min_tokens_to_keep,
            )

    return (
        [payloads[name] for name in ordered_names if payloads[name] is not None],
        has_post_topp,
        native_pre_warper,
        tuple(ordered_names),
    )


def build_sampling_plan(
    logits_processors: Optional[LogitsProcessorList],
    *,
    do_sample: bool,
    temperature: float,
    top_p: float,
) -> SamplingPlan:
    """Place custom processors without duplicating active standard warpers."""
    pre_warper = []
    post_topp = []
    external_processors = []
    has_declarative_order = False
    for processor in list(logits_processors or []):
        is_external = bool(getattr(processor, "_codewm_external_processor", False))
        raw_placement = getattr(processor, "_codewm_placement", None)
        if not is_external:
            pre_warper.append(processor)
            continue
        external_processors.append(processor)
        if getattr(processor, "_codewm_decode_order", None) is not None:
            has_declarative_order = True
            continue
        if raw_placement is None:
            method = getattr(processor, "_codewm_method", processor.__class__.__name__)
            raise ValueError(f"external watermark processor '{method}' has no placement")
        try:
            placement = WatermarkPlacement(raw_placement)
        except ValueError as exc:
            raise ValueError(f"unsupported watermark placement: {raw_placement!r}") from exc
        if placement is WatermarkPlacement.PRE_WARPER:
            pre_warper.append(processor)
        elif placement is WatermarkPlacement.POST_TOPP:
            post_topp.append(processor)
        else:
            raise ValueError(f"unsupported watermark placement: {placement!r}")

    if has_declarative_order:
        ordered_nodes, has_post_topp, native_pre_warper, graph_nodes = (
            _topological_sampling_nodes(
                external_processors,
                do_sample=do_sample,
                temperature=temperature,
                top_p=top_p,
            )
        )
        execution_backend = (
            "topology_native" if native_pre_warper else "topology_explicit"
        )
        for processor in external_processors:
            processor._codewm_sampling_backend = execution_backend
            processor._codewm_compiled_graph = graph_nodes
        planned_processors = [
            *[
                processor
                for processor in pre_warper
                if not bool(getattr(processor, "_codewm_external_processor", False))
            ],
            *ordered_nodes,
        ]
        if native_pre_warper:
            return SamplingPlan(
                logits_processors=LogitsProcessorList(planned_processors),
                host_temperature=temperature,
                host_top_p=top_p,
                host_top_k=None,
                has_post_topp=False,
                execution_backend=execution_backend,
                decode_graph_nodes=graph_nodes,
            )
        return SamplingPlan(
            logits_processors=LogitsProcessorList(planned_processors),
            host_temperature=1.0,
            host_top_p=1.0,
            host_top_k=0,
            has_post_topp=has_post_topp,
            execution_backend=execution_backend,
            decode_graph_nodes=graph_nodes,
        )

    if not post_topp:
        return SamplingPlan(
            logits_processors=(
                LogitsProcessorList(pre_warper) if pre_warper else None
            ),
            host_temperature=temperature,
            host_top_p=top_p,
            host_top_k=None,
            has_post_topp=False,
            execution_backend="legacy_native",
        )

    _ensure_post_topp_host_warpers_supported()
    explicit_processors = list(pre_warper)
    if do_sample:
        min_tokens_to_keep = _min_tokens_to_keep()
        if temperature != 1.0:
            explicit_processors.append(TemperatureLogitsWarper(float(temperature)))
        top_k = int(getattr(model.generation_config, "top_k", 0) or 0)
        if top_k != 0:
            explicit_processors.append(
                TopKLogitsWarper(
                    top_k=top_k,
                    min_tokens_to_keep=min_tokens_to_keep,
                )
            )
        if top_p < 1.0:
            explicit_processors.append(
                TopPLogitsWarper(
                    top_p=float(top_p),
                    min_tokens_to_keep=min_tokens_to_keep,
                )
            )
    explicit_processors.extend(post_topp)
    return SamplingPlan(
        logits_processors=LogitsProcessorList(explicit_processors),
        host_temperature=1.0,
        host_top_p=1.0,
        host_top_k=0,
        has_post_topp=True,
        execution_backend="legacy_explicit",
    )

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


def extract_continuation_rows(
    seqs: torch.LongTensor,
    prompt_len: int,
    new_lens: Sequence[int],
) -> List[List[int]]:
    """Extract authoritative per-row continuation IDs from generate output."""
    if seqs.ndim != 2:
        raise ValueError(
            f"expected rank-2 generated sequences, got shape={tuple(seqs.shape)}"
        )
    if len(new_lens) != int(seqs.shape[0]):
        raise ValueError(
            "generated row count does not match continuation length accounting: "
            f"rows={int(seqs.shape[0])}, lengths={len(new_lens)}"
        )

    rows: List[List[int]] = []
    for row_index, new_len in enumerate(new_lens):
        stop = int(prompt_len) + int(new_len)
        rows.append(
            [
                int(token)
                for token in seqs[row_index, int(prompt_len):stop]
                .detach()
                .cpu()
                .tolist()
            ]
        )
    return rows


def finalize_generation_evidence(
    logits_processors: Optional[LogitsProcessorList],
    continuation_rows: Sequence[Sequence[int]],
) -> None:
    """Synchronize complete generated IDs into opt-in detector evidence sinks."""
    for processor in list(logits_processors or []):
        finalizer = getattr(
            processor,
            "_codewm_generation_evidence_finalizer",
            None,
        )
        if callable(finalizer):
            finalizer(processor, continuation_rows)


class _PostSampleObserver(StoppingCriteria):
    """No-op stopping criterion that publishes newly sampled token IDs."""

    def __init__(self, prompt_len: int, callbacks: Sequence[Any]):
        self.prompt_len = int(prompt_len)
        self.callbacks = tuple(callbacks)
        self.observed_steps = 0

    def __call__(self, input_ids: torch.LongTensor, scores: Any, **kwargs) -> torch.BoolTensor:
        generated_steps = max(0, int(input_ids.shape[1]) - self.prompt_len)
        from processors import SampledTokenEvent

        while self.observed_steps < generated_steps:
            self.observed_steps += 1
            stop = self.prompt_len + self.observed_steps
            token_ids = tuple(int(row[stop - 1].item()) for row in input_ids)
            sequence_ids = tuple(
                tuple(int(token) for token in row[:stop].detach().cpu().tolist())
                for row in input_ids
            )
            event = SampledTokenEvent(
                step=self.observed_steps,
                token_ids=token_ids,
                sequence_ids=sequence_ids,
            )
            for callback in self.callbacks:
                callback(event)
        return torch.zeros(input_ids.shape[0], dtype=torch.bool, device=input_ids.device)


def build_post_sample_observer(
    logits_processors: Optional[LogitsProcessorList],
    prompt_len: int,
) -> Optional[StoppingCriteriaList]:
    callbacks = []
    for processor in list(logits_processors or []):
        callback = getattr(processor, "codewm_on_sampled_token", None)
        if callback is None:
            callback = getattr(processor, "_codewm_on_sampled_token", None)
        if callable(callback):
            callbacks.append(callback)
    if not callbacks:
        return None
    return StoppingCriteriaList([_PostSampleObserver(prompt_len, callbacks)])

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
    sampling_plan = build_sampling_plan(
        logits_processors,
        do_sample=do_sample,
        temperature=temperature,
        top_p=top_p,
    )
    # Private generator path for deterministic sampling (recommended)
    seed_to_use = pick_seed(rng_seed, input_ids) if do_sample else None
    gen = None
    if do_sample and seed_to_use is not None:
        gen = torch.Generator(device=input_ids.device)
        gen.manual_seed(seed_to_use)

    def _call_generate(gen_arg):
        post_sample_observer = build_post_sample_observer(logits_processors, prompt_len)
        generate_kwargs = dict(
            input_ids=input_ids,
            attention_mask=attn,
            do_sample=do_sample,
            temperature=sampling_plan.host_temperature,
            top_p=sampling_plan.host_top_p,
            max_new_tokens=capped,
            logits_processor=sampling_plan.logits_processors,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=model.generation_config.eos_token_id,
            generator=gen_arg,
            return_dict_in_generate=True,
        )
        if sampling_plan.host_top_k is not None:
            generate_kwargs["top_k"] = sampling_plan.host_top_k
        if post_sample_observer is not None:
            generate_kwargs["stopping_criteria"] = post_sample_observer
        return model.generate(**generate_kwargs)

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
    continuation_rows = extract_continuation_rows(seqs, prompt_len, new_lens)
    finalize_generation_evidence(logits_processors, continuation_rows)
    text = tokenizer.batch_decode(seqs[:, prompt_len:], skip_special_tokens=True)[0]
    comp = new_lens[0]
    total = prompt_len + comp

    return text, prompt_len, comp, total, reasons[0], float(t1 - t0)
