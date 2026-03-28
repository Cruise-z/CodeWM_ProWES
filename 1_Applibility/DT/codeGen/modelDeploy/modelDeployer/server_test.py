# server.py
# pip install "transformers>=4.41" fastapi uvicorn pydantic torch accelerate
import time
import asyncio
from typing import Any, Dict, List, Optional, Union, Callable
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, PrivateAttr
import torch
import copy
import json
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from transformers import (
    AutoModelForCausalLM, AutoTokenizer,
    LogitsProcessorList, TopPLogitsWarper, TopKLogitsWarper, TemperatureLogitsWarper,
    LogitsProcessor
)
from transformers.generation.stopping_criteria import (
    StoppingCriteriaList, MaxLengthCriteria
)

# ================= Configuration (sampling on/off and dual-branch setup) =================
import os
# SERVER_DO_SAMPLE: "1"/"true" enables sampling; "0"/"false" uses greedy decoding. Enabled by default.
def _as_bool(x: str) -> bool:
    return str(x).strip().lower() not in ("0", "false", "no", "off", "")
SERVER_DO_SAMPLE = _as_bool(os.getenv("SERVER_DO_SAMPLE", "1"))
# SAMPLING_MODE: "lenient_openai" | "map_to_greedy" | "strict"
# See normalize_sampling_args() below for details. Default: "lenient_openai".
def _as_mode(x: str) -> str:
    """Normalize a string into one of {'lenient_openai', 'map_to_greedy', 'strict'}."""
    s = str(x or "").strip().lower().replace("-", "_")
    if s in ("lenient_openai", "lenient", "openai", "lo"):
        return "lenient_openai"
    if s in ("map_to_greedy", "map2greedy", "to_greedy", "greedy_map", "mg"):
        return "map_to_greedy"
    if s in ("strict", "error", "raise", "s"):
        return "strict"
    # Fall back to the lenient mode if the value is unrecognized
    return "lenient_openai"
SAMPLING_MODE = _as_mode(os.getenv("SAMPLING_MODE", "lenient_openai"))

# Whether to require external_processor_names in parallel mode, to avoid mistakenly using identical configurations on both branches
REQUIRE_EXTERNAL_IN_PARALLEL = _as_bool(os.getenv("REQUIRE_EXTERNAL_IN_PARALLEL", "0"))

# ====== Raw request-body logging control (disabled by default, enable when needed) ======
# LOG_REQ_BODY=1 enables body logging; LOG_REQ_BODY_BYTES controls the maximum number of raw bytes to print
LOG_REQ_BODY = _as_bool(os.getenv("LOG_REQ_BODY", "0"))
LOG_REQ_BODY_BYTES = int(os.getenv("LOG_REQ_BODY_BYTES", "4096"))

# ================= Model loading (no built-in watermark enabled by default) =================
MODEL_ID = "Qwen/Qwen2.5-Coder-32B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID, torch_dtype=torch.bfloat16, device_map="cuda"
)
model.eval()
# === Pre-generation tokenizer/model fallback configuration to avoid warnings or out-of-range issues when pad is missing ===
try:
    if tokenizer.pad_token_id is None and tokenizer.eos_token_id is not None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    if getattr(model, "config", None) is not None:
        cfg = model.config
        if getattr(cfg, "pad_token_id", None) is None and tokenizer.pad_token_id is not None:
            cfg.pad_token_id = tokenizer.pad_token_id
        if getattr(cfg, "eos_token_id", None) is None and tokenizer.eos_token_id is not None:
            cfg.eos_token_id = tokenizer.eos_token_id
except Exception:
    # This fallback should not affect the main flow, so fail silently
    pass

# Vocabulary IDs used to construct your processors, fully consistent with this service's tokenizer
vocab_ids: List[int] = list(tokenizer.get_vocab().values())

# ================= Processor registries and registration helpers =================
# You can register "HF built-in watermarking / your custom watermarking" on either side as you prefer
# Register **factory functions** and instantiate them at request parsing time to avoid sharing mutable state across requests
ProcessorFactory = Callable[[], LogitsProcessorList]
INTERNAL_PROCESSORS: Dict[str, ProcessorFactory] = {}
EXTERNAL_PROCESSORS: Dict[str, ProcessorFactory] = {} # Kept for type/API compatibility, but no longer used during request resolution

# ===== Pure builder-based flow: external processors are instantiated dynamically via parameterizable builders =====
ParametricBuilder = Callable[..., Any]
EXTERNAL_BUILDERS: Dict[str, ParametricBuilder] = {}

def register_external_builder(name: str, builder: ParametricBuilder) -> None:
    """
    Register a parameterizable external-processor builder. The request side can pass parameters through external_processor_params[name].
    vocab=vocab_ids is forced here, and any incoming vocab argument is ignored.
    """
    if not callable(builder):
        raise TypeError(f"external builder for '{name}' must be callable")
    EXTERNAL_BUILDERS[name] = builder

def _ensure_lp_list(p) -> LogitsProcessorList:
    """
    Normalize an object into LogitsProcessorList and enforce strict type validation:
      - None is forbidden
      - Allowed inputs: a single LogitsProcessor, a LogitsProcessorList, or list/tuple[LogitsProcessor]
    """
    if p is None:
        raise TypeError("LogitsProcessor is None (expected LogitsProcessor or LogitsProcessorList).")
    if isinstance(p, LogitsProcessorList):
        for it in p:
            if not isinstance(it, LogitsProcessor):
                raise TypeError(f"Invalid item in LogitsProcessorList: {type(it)}")
        return p
    if isinstance(p, LogitsProcessor):
        return LogitsProcessorList([p])
    if isinstance(p, (list, tuple)):
        if not all(isinstance(it, LogitsProcessor) for it in p):
            bad = [type(it) for it in p if not isinstance(it, LogitsProcessor)]
            raise TypeError(f"Invalid items in processor list: {bad}")
        return LogitsProcessorList(list(p))
    raise TypeError(f"Expected LogitsProcessor/LogitsProcessorList/list[LogitsProcessor], got {type(p)}")

def _as_factory(factory_or_obj: Any) -> ProcessorFactory:
    """
    Convert any supported input into a zero-argument factory:
      1) If it is already a processor instance (even if callable), treat it as an instance and return a clone each time;
      2) Otherwise, if it is a callable zero-argument factory, call it and validate the result;
    """
    # Prefer handling concrete instances first (LogitsProcessor / LogitsProcessorList / list/tuple[LogitsProcessor])
    if isinstance(factory_or_obj, (LogitsProcessor, LogitsProcessorList, list, tuple)):
        inst_lp = _ensure_lp_list(factory_or_obj)
        def _factory_from_instance() -> LogitsProcessorList:
            return _clone_lp_list(inst_lp)
        return _factory_from_instance
    # Only then treat a callable object as a zero-argument factory
    if callable(factory_or_obj):
        def _factory_from_callable() -> LogitsProcessorList:
            prod = factory_or_obj()
            return _ensure_lp_list(prod)
        return _factory_from_callable
    raise TypeError(
        f"register_* expects a LogitsProcessor/LogitsProcessorList/list[LogitsProcessor] "
        f"or a zero-arg factory that returns one, got {type(factory_or_obj)}"
    )

def register_internal(name: str, factory_or_obj: Any) -> None:
    """Register into the internal processor namespace, stored as a factory."""
    INTERNAL_PROCESSORS[name] = _as_factory(factory_or_obj)

def register_external(name: str, factory_or_obj: Any) -> None:
    """
    Compatibility helper kept in case older code still calls it, but EXTERNAL_PROCESSORS is no longer used during request resolution.
    If called, it only registers the object and does not participate in the generation path.
    """
    EXTERNAL_PROCESSORS[name] = _as_factory(factory_or_obj)

def _clone_lp_list(lp: LogitsProcessorList) -> LogitsProcessorList:
    """
    Clone processor instances per request to avoid cross-request or cross-branch state interference.
    If deepcopy fails, fall back to the original object rather than blocking execution.
    """
    new = []
    for p in lp:
        try:
            new.append(copy.deepcopy(p))
        except Exception:
            new.append(p)
    return LogitsProcessorList(new)

def _resolve_lp_list(
    internal_names: Optional[List[str]],
    external_names: Optional[List[str]],
    mode: str,  # "internal_only" | "internal_plus_external" | "any"
    *,
    external_params: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Optional[LogitsProcessorList]:
    """Resolve multiple named processors into a single LogitsProcessorList while preserving the input order.
       Convention: in parallel mode, internal processors come before external processors; the same ordering is also used in single-branch mode.
    """
    chain: List[Any] = []

    if internal_names:
        for n in internal_names:
            if n not in INTERNAL_PROCESSORS:
                raise HTTPException(status_code=400, detail=f"Unknown internal processor: {n}")
            # Instantiate the factory to get an independent processor chain for this request
            try:
                lp = INTERNAL_PROCESSORS[n]()
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Internal processor '{n}' factory error: {e}") from e
            # Validate each produced item strictly
            for it in lp:
                if not isinstance(it, LogitsProcessor):
                    raise HTTPException(status_code=400, detail=f"Internal processor '{n}' produced invalid item: {type(it)}")
            chain.extend(lp)

    if mode != "internal_only" and external_names:
        for n in external_names:
            if n not in EXTERNAL_BUILDERS:
                # Pure builder-based flow: fail immediately if the builder is not registered
                raise HTTPException(status_code=400, detail=f"Unknown external builder: {n}")
            # Read parameters from the request and forcefully override vocab
            cfg = dict((external_params or {}).get(n) or {})
            cfg.pop("vocab", None)
            try:
                obj = EXTERNAL_BUILDERS[n](vocab=vocab_ids, **cfg)
                lp = _ensure_lp_list(obj)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"External builder '{n}' error: {e}") from e
            for it in lp:
                if not isinstance(it, LogitsProcessor):
                    raise HTTPException(status_code=400, detail=f"External builder '{n}' produced invalid item: {type(it)}")
            chain.extend(lp)

    if not chain:
        return None
    return LogitsProcessorList(chain)

# ===== Insert optional auto-loading of uiAPI / processor registration here =====
try:
    import importlib, sys, os
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    importlib.import_module("regWM")  # register_xxx should be called at module top level inside regWM
    print("[server] processors loaded ->",
          "internal:", list(INTERNAL_PROCESSORS.keys()),
          "external_builders:", list(EXTERNAL_BUILDERS.keys()))
except Exception as e:
    print(f"[server] regWM not loaded: {e}")

# ================== OpenAI-compatible request/response models ==================
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: Optional[str] = MODEL_ID
    messages: List[Message]
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.95
    max_tokens: Optional[int] = 512
    stream: Optional[bool] = False  # Streaming is not implemented in this example
    # Optional: fix the random seed for this request to guarantee reproducibility across runs; coupling is still possible if omitted
    rng_seed: Optional[int] = None

    # The processor-name interfaces you care about (all lists); names must be registered beforehand
    internal_processor_names: Optional[List[str]] = None
    external_processor_names: Optional[List[str]] = None

    # Parallel switch: when True, return results for two branches, internal-only and internal-plus-external
    parallel: Optional[bool] = False
    # Only applies to external processors: pass builder arguments by name
    external_processor_params: Optional[Dict[str, Dict[str, Any]]] = None
    
    # Hidden switch: does not appear in schema and cannot be passed in by clients
    _do_sample: bool = PrivateAttr(default=SERVER_DO_SAMPLE)

# Normalize incoming sampling arguments
def normalize_sampling_args(do_sample: bool,
                            temperature: Optional[float],
                            top_p: Optional[float],
                            mode: str = SAMPLING_MODE):
    """
    mode:
      - "lenient_openai": if do_sample=True and temp<=0, use temp=1e-4; if do_sample=False, force temp=1.0 and top_p=1.0
      - "map_to_greedy":  if do_sample=True and temp<=0, switch do_sample=False (convert to greedy)
      - "strict":         if do_sample=True and temp<=0, raise ValueError
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
        else:  # "strict"
            raise ValueError("temperature must be > 0 when do_sample=True")

    # Constrain top_p to (0, 1]
    if not (0 < p <= 1.0):
        p = 1.0

    return True, t, p

app = FastAPI()

# ====== Simple request-body size logging middleware, enabled only on selected routes ======
logger = logging.getLogger("server")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

class LogReqSizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Adjust the set of tracked paths as needed
        if request.url.path in ("/v1/chat/completions", "/dbg/echo-len"):
            try:
                body = await request.body()          # Starlette caches it, so it can be read again later
                size = len(body or b"")
                cl = request.headers.get("content-length")
                # Try to parse the parallel field to make parallel stress tests easier to inspect
                parallel = None
                try:
                    data = json.loads(body.decode("utf-8"))
                    parallel = data.get("parallel", None)
                except Exception:
                    pass
                logger.info("[recv] bytes=%s content-length=%s path=%s parallel=%s",
                            size, cl, request.url.path, parallel)
                # Optional: print the request body, limited by LOG_REQ_BODY / LOG_REQ_BODY_BYTES
                if LOG_REQ_BODY:
                    preview = body[:LOG_REQ_BODY_BYTES]
                    # Prefer JSON pretty-print first; if that fails, fall back to plain text
                    printed = None
                    try:
                        parsed = json.loads(preview.decode("utf-8", "replace"))
                        printed = json.dumps(parsed, ensure_ascii=False, indent=2)
                    except Exception:
                        printed = preview.decode("utf-8", "replace")
                    # Include preview length and total size so the output is not mistaken for the full body
                    logger.info(
                        "[recv] body_preview(%d/%dB): %s",
                        len(preview), size, printed
                    )
            except Exception as e:
                logger.warning("[recv] failed to read body: %r", e)
        return await call_next(request)

app.add_middleware(LogReqSizeMiddleware)

@app.get("/v1/_processors")
def list_processors():
    """Debug endpoint: inspect the currently registered processor names."""
    return {
        "internal": list(INTERNAL_PROCESSORS.keys()),
        "external": list(EXTERNAL_PROCESSORS.keys()),     # Kept for compatibility display
        "external_builders": list(EXTERNAL_BUILDERS.keys())
    }
    
@app.get("/v1/models")
def list_models():
    """OpenAI-compatible endpoint: list the single available model."""
    return {"object": "list", "data": [{"id": MODEL_ID, "object": "model"}]}

# ====== Debug endpoint: return request-body length ======
@app.post("/dbg/echo-len")
async def dbg_echo_len(request: Request):
    try:
        body = await request.body()
        cl = request.headers.get("content-length")
        return {"len": len(body or b""), "content_length": cl}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"echo_len_error: {e}")

def _model_ctx_limit() -> Optional[int]:
    """
    Infer the model's maximum supported context length in tokens.
    Different models/configs use different field names, so this function applies a compatibility fallback.
    If rope_scaling exists, as in some Llama/Qwen variants, it estimates the effective limit by factor.
    Return None when a reliable inference is not possible.
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
    # rope_scaling inference, if present
    try:
        rs = getattr(cfg, "rope_scaling", None)
        if isinstance(rs, dict):
            factor = rs.get("factor") or rs.get("rope_factor")
            if factor:
                base = int(base * float(factor))
    except Exception:
        pass
    return base

def _cap_max_new_tokens(prompt_len: int, want_new: Optional[int]) -> int:
    ctx = _model_ctx_limit()
    safe = int(want_new or 0)
    return max(0, min(safe, (ctx - prompt_len) if isinstance(ctx, int) else safe))

@app.get("/healthz")
def healthz():
    """Simple health check endpoint, useful for load-balancer probing."""
    return {"status": "ok", "model": MODEL_ID}

def _is_cache_obj(pkv) -> bool:
    """
    Determine whether this is a newer-style transformers Cache object, such as StaticCache/DynamicCache.
    Such objects usually provide methods like get_seq_length()/get_max_capacity().
    """
    if pkv is None:
        return False
    cls_name = pkv.__class__.__name__.lower()
    return hasattr(pkv, "get_seq_length") or cls_name.endswith("cache")
    
def _prefill_and_expand_kv(input_ids: torch.Tensor,
                           attn: torch.Tensor,
                           times: int = 2):
    """
    First run a batch=1 prefill, then try to copy past_key_values along the batch dimension into multiple branches.
    If copying fails, for example because a newer Cache abstraction or non-tensor structure is encountered,
    fall back to a batch=times prefill instead, which recomputes the prompt once more but preserves compatibility.
    Returns: (pkv_batched, last_logits_batched[times, vocab], used_fallback: bool)
    """
    prefill = model(input_ids=input_ids, attention_mask=attn, use_cache=True)
    pkv = prefill.past_key_values
    last_logits_1 = prefill.logits[:, -1, :]  # [1, vocab]
    # New-style Cache: do not copy it, directly fall back to a batch=times prefill, which is stable and aligned with model expectations
    if _is_cache_obj(pkv):
        ids2 = input_ids.repeat(times, 1).contiguous()
        attn2 = attn.repeat(times, 1).contiguous()
        prefill2 = model(input_ids=ids2, attention_mask=attn2, use_cache=True)
        pkv2 = prefill2.past_key_values
        last_logits_batched = prefill2.logits[:, -1, :]  # [times, vocab]
        return pkv2, last_logits_batched, True

    # Legacy tuple/list format: try to copy the KV cache across the batch dimension
    try:
        pkv_batched = _repeat_pkv(pkv, times=times)
        last_logits_batched = last_logits_1.repeat(times, 1)
        return pkv_batched, last_logits_batched, False
    except Exception:
        # Final fallback: directly run a batch=times prefill
        pass

    # Fallback
    ids2 = input_ids.repeat(times, 1).contiguous()
    attn2 = attn.repeat(times, 1).contiguous()
    prefill2 = model(input_ids=ids2, attention_mask=attn2, use_cache=True)
    pkv2 = prefill2.past_key_values
    last_logits_batched = prefill2.logits[:, -1, :]  # [times, vocab]
    return pkv2, last_logits_batched, True

def _repeat_pkv(pkv, times: int = 2):
    """
    Duplicate single-branch past_key_values across the batch dimension into multiple branches.
    Compatible with the pkv structure used by most HF models: tuple[layer] -> tuple[tensor...]
    """
    if pkv is None:
        return None
    # Allow copying only for legacy tuple/list structures; newer Cache objects raise immediately and trigger the fallback path
    if not isinstance(pkv, (tuple, list)):
        raise TypeError(f"repeat_pkv expects legacy tuple/list, got {type(pkv)}")
    rep_layers = []
    # Some implementations return a list; handle all cases uniformly as iterable layers
    for layer in pkv:  # type: ignore[assignment]
        if not isinstance(layer, (tuple, list)):
            raise TypeError("unexpected PKV layer type; expected tuple/list of tensors")
        rep_tensors = []
        for t in layer:
            rep_tensors.append(torch.repeat_interleave(t, repeats=times, dim=0) if torch.is_tensor(t) else t)
        rep_layers.append(tuple(rep_tensors))
    return tuple(rep_layers)

def _prep_inputs(messages: List[Dict[str, str]]) -> Dict[str, torch.Tensor]:
    chat_text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    return tokenizer([chat_text], return_tensors="pt").to(model.device)

def _safe_get_logits_processor(gen_cfg, prompt_len: int) -> LogitsProcessorList:
    """
    Compatibly obtain HF's logits_processor; fall back to an empty list if the model lacks the relevant private method.
    """
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

def _safe_get_logits_warper(gen_cfg) -> LogitsProcessorList:
    """
    Compatibly obtain HF's warpers; if the model lacks the relevant private method, build them manually from temperature / top_p.
    """
    try:
        return model._get_logits_warper(gen_cfg)
    except Exception:
        warpers = LogitsProcessorList([])
        if getattr(gen_cfg, "do_sample", False):
            # temperature
            temp = float(getattr(gen_cfg, "temperature", 1.0) or 1.0)
            if abs(temp - 1.0) > 1e-6:
                warpers.append(TemperatureLogitsWarper(temp))
            # top_p
            tp = float(getattr(gen_cfg, "top_p", 1.0) or 1.0)
            if 0.0 < tp < 1.0:
                warpers.append(TopPLogitsWarper(tp))
            # If top_k support is needed, append TopKLogitsWarper here as needed
        return warpers

def _safe_get_stopping_criteria(gen_cfg) -> StoppingCriteriaList:
    """
    Compatibly obtain HF's stopping_criteria; return an empty list if the model lacks the relevant private method.
    """
    try:
        return model._get_stopping_criteria(gen_cfg, None)
    except Exception:
        return StoppingCriteriaList([])
    
def _stopping_met(stopping_criteria: StoppingCriteriaList,
                  input_ids: torch.Tensor,
                  scores: Optional[torch.Tensor] = None) -> bool:
    """
    Normalize the return value of StoppingCriteriaList into a bool.
    - Standard implementations return bool;
    - If some custom criteria return a BoolTensor with shape=[B], reduce it via any();
    - For other truthy/falsy objects, use bool().
    If an error occurs, safely treat it as "stop not triggered".
    """
    try:
        out = stopping_criteria(input_ids, scores)
        if isinstance(out, bool):
            return out
        if torch.is_tensor(out):
            # Support both 0-d and 1-d shapes, where 1-d may correspond to the batch dimension
            return bool(out.any().item())
        return bool(out)
    except Exception:
        return False

@torch.inference_mode()
def _build_hf_components(
    prompt_len: int,
    do_sample: bool,
    temperature: Optional[float],
    top_p: Optional[float],
    max_new_tokens: int,
) -> tuple:
    """
    Reuse HF generation subcomponents by building them from normalized sampling arguments:
    - hf_logits_processor: HF's built-in processors, such as no_repeat_ngram/repetition_penalty/...
    - hf_warpers: HF's built-in warpers, such as temperature/top_p/top_k/...
    - stopping_criteria: HF stopping criteria, supplemented with MaxLengthCriteria(prompt_len+max_new_tokens)
    """
    # Clone a copy to avoid mutating the global config
    gen_cfg = copy.deepcopy(model.generation_config)
    gen_cfg.do_sample = bool(do_sample)
    if temperature is not None:
        gen_cfg.temperature = float(temperature)
    if top_p is not None:
        gen_cfg.top_p = float(top_p)
    # Make sure stopping criteria can see max_length semantics, derived from max_new_tokens
    # Note: HF typically combines max_new_tokens with the current length internally; here it is filled in explicitly
    max_len = int(prompt_len + max_new_tokens) if max_new_tokens and max_new_tokens > 0 else int(prompt_len)

    # Note: HF private methods may not exist on some models, so use a safe fallback here
    hf_lp = _safe_get_logits_processor(gen_cfg, prompt_len)
    hf_warpers = _safe_get_logits_warper(gen_cfg)
    stopping_criteria = _safe_get_stopping_criteria(gen_cfg)
    # Add MaxLengthCriteria if it is missing, using prompt_len+max_new_tokens as the cap
    has_maxlen = any(isinstance(c, MaxLengthCriteria) for c in stopping_criteria)
    if not has_maxlen:
        stopping_criteria.append(MaxLengthCriteria(max_length=max_len))
    return gen_cfg, hf_lp, hf_warpers, stopping_criteria

@torch.inference_mode()
def _gen_internal_like_parallel(
    inputs: Dict[str, torch.Tensor],
    lp_internal: Optional[LogitsProcessorList],
    temperature: float,
    top_p: float,
    max_new_tokens: int,
    do_sample: bool = SERVER_DO_SAMPLE,
    rng_seed: Optional[int] = None,
) -> tuple[str, int, int, int]:
    """
    Single-branch generation that stays **fully aligned** with the "internal-only" branch in parallel mode:
      - Shares the same HF subcomponents (hf_logits_processor + hf_warpers)
      - Uses the same step-by-step forward progression and stop logic as the parallel path
      - Uses the same U(0,1) CDF sampling path as the parallel version via self-coupled sampling
    """
    device = next(model.parameters()).device
    input_ids = inputs["input_ids"].to(device)  # [1, L]
    attn = inputs.get("attention_mask", None)
    if attn is None:
        attn = torch.ones_like(input_ids, dtype=torch.long, device=device)
    else:
        attn = attn.to(device)

    prompt_len = int(input_ids.shape[1])
    try:
        want = int(max_new_tokens or 0)
    except Exception:
        want = 0
    max_new_tokens = _cap_max_new_tokens(prompt_len, want)
    if max_new_tokens <= 0:
        return "", prompt_len, 0, prompt_len

    # Normalize sampling arguments and build HF subcomponents from them
    do_sample, temperature, top_p = normalize_sampling_args(do_sample, temperature, top_p)
    _, hf_lp, hf_warpers, stopping_criteria = _build_hf_components(
        prompt_len, do_sample, temperature, top_p, max_new_tokens
    )
    lp0_full = LogitsProcessorList(list(hf_lp) + list(lp_internal or []))

    # Shared random source, using the same seed derivation as the parallel path
    gen = None
    if do_sample:
        gen = torch.Generator(device=device)
        seed = int(torch.sum(input_ids).item() % (2**31 - 1)) if rng_seed is None else int(rng_seed)
        gen.manual_seed(seed)

    # Prefill
    pkv, last_logits_b1, _ = _prefill_and_expand_kv(input_ids, attn, times=1)
    cur_ids = input_ids.clone()
    cur_attn = attn.clone()

    # Stop token
    eos_token_id = model.generation_config.eos_token_id
    eos_ids: List[int] = []
    if isinstance(eos_token_id, int) and eos_token_id >= 0:
        eos_ids = [eos_token_id]
    elif isinstance(eos_token_id, (list, tuple)):
        eos_ids = [int(x) for x in eos_token_id if x is not None]

    finished = False
    comp_tok = 0

    def _apply(proc: Optional[LogitsProcessorList], ids_ctx: torch.Tensor, scores: torch.Tensor) -> torch.Tensor:
        if proc is not None:
            scores = proc(ids_ctx, scores)
        return scores

    # First step: use the logits from the last prefill position
    scores0 = _apply(lp0_full, cur_ids, last_logits_b1)  # [1,V]
    if do_sample and len(hf_warpers):
        scores0 = hf_warpers(cur_ids, scores0)
    # Self-coupled sampling, ensuring the exact same sampling distribution / numeric path as the parallel internal-only branch
    tok0, _ = _coupled_pick_from_scores(scores0, scores0, do_sample, generator=gen)
    comp_tok += 1
    if eos_ids and int(tok0.item()) in eos_ids:
        finished = True
    cur_ids = torch.cat([cur_ids, tok0], dim=1)
    cur_attn = torch.cat([cur_attn, torch.ones((1,1), dtype=cur_attn.dtype, device=device)], dim=1)
    # Check HF stopping criteria, including length
    if stopping_criteria(cur_ids, None):
        finished = True

    steps = 1
    while steps < max_new_tokens:
        if finished:
            break
        step_in = cur_ids[:, -1:].contiguous()
        outputs = model(
            input_ids=step_in,
            attention_mask=cur_attn,
            past_key_values=pkv,
            use_cache=True
        )
        pkv = outputs.past_key_values
        logits = outputs.logits[:, -1, :]  # [1,V]
        scores0 = _apply(lp0_full, cur_ids, logits)
        if do_sample and len(hf_warpers):
            scores0 = hf_warpers(cur_ids, scores0)
        tok0, _ = _coupled_pick_from_scores(scores0, scores0, do_sample, generator=gen)
        comp_tok += 1
        if eos_ids and int(tok0.item()) in eos_ids:
            finished = True
        cur_ids = torch.cat([cur_ids, tok0], dim=1)
        cur_attn = torch.cat([cur_attn, torch.ones((1,1), dtype=cur_attn.dtype, device=device)], dim=1)
        # Check HF stopping criteria, including length
        if stopping_criteria(cur_ids, None):
            finished = True
        steps += 1

    text = tokenizer.batch_decode(cur_ids[:, prompt_len:], skip_special_tokens=True)[0]
    prompt_tok = int(inputs["input_ids"].shape[1])
    total_tok = prompt_tok + comp_tok
    return text, prompt_tok, comp_tok, total_tok

@torch.inference_mode()
def _coupled_pick_from_scores(
    scores0: torch.Tensor, scores1: torch.Tensor, do_sample: bool, *,
    generator: Optional[torch.Generator] = None
) -> tuple[torch.Tensor, torch.Tensor]:
    """
    Coupled sampling using shared random numbers:
      - do_sample=False: both branches use argmax, giving fully deterministic matching behavior
      - do_sample=True:  sample a shared u~U(0,1), then sample both branches against their own probability CDFs using that same u
    Input shape: scoresX [1, vocab], and returned token ids both have shape [1,1]
    """
    if not do_sample:
        tok0 = scores0.argmax(dim=-1, keepdim=True)
        tok1 = scores1.argmax(dim=-1, keepdim=True)
        return tok0, tok1
    # softmax -> probability; note float32 stability
    p0 = torch.softmax(scores0, dim=-1).to(torch.float32)  # [1,V]
    p1 = torch.softmax(scores1, dim=-1).to(torch.float32)  # [1,V]
    # Shared random number u
    if generator is None:
        u = torch.rand((), device=scores0.device)
    else:
        u = torch.rand((), device=scores0.device, generator=generator)
    # Numerical safety: avoid out-of-range hits in extreme cases where u==1
    eps = torch.finfo(p0.dtype).eps
    u = torch.clamp(u, eps, 1 - eps)
    # CDF search
    cdf0 = p0.cumsum(dim=-1).squeeze(0)  # [V]
    cdf1 = p1.cumsum(dim=-1).squeeze(0)  # [V]
    # Boundary protection: under extreme numerics the CDF tail may be < 1, so searchsorted may return V
    i0 = torch.searchsorted(cdf0, u).clamp(max=cdf0.numel() - 1).long().item()
    i1 = torch.searchsorted(cdf1, u).clamp(max=cdf1.numel() - 1).long().item()
    return (torch.tensor([[i0]], device=scores0.device, dtype=torch.long),
            torch.tensor([[i1]], device=scores1.device, dtype=torch.long))

@torch.inference_mode()
def _dual_sync_generate_internal_base(
    inputs: Dict[str, torch.Tensor],
    lp_internal: Optional[LogitsProcessorList],   # Internal chain only
    lp_external: Optional[LogitsProcessorList],   # External chain only, may be None
    temperature: float,
    top_p: float,
    max_new_tokens: int,
    eos_token_id: Optional[Union[int, List[int]]] = None,
    min_new_tokens: int = 0,
    do_sample: bool = SERVER_DO_SAMPLE,           # Added; defaults to the global setting
    rng_seed: Optional[int] = None,
) -> tuple[str, str, int, int, int, List[bool]]:
    """
    Synchronized forked parallel generation, using the internal-processed distribution as the baseline and avoiding duplicate prompt forward passes:
    - Each step performs only one forward pass to obtain logits;
    - scores_internal = internal processor chain(logits), used as the baseline distribution;
      * internal_only branch: sample directly from scores_internal;
      * internal_plus_external branch: apply the external chain on scores_internal.clone() and then sample.
    - The two branches advance their own sequences independently, while sharing the batch=2 KV cache.
    Returns: (text_internal_only, text_internal_plus_external, prompt_tok, completion_tok_sum, total_tok, finished[List[bool]])
    """
    device = next(model.parameters()).device
    input_ids = inputs["input_ids"].to(device)  # [1, L]
    attn = inputs.get("attention_mask", None)
    if attn is None:
        attn = torch.ones_like(input_ids, dtype=torch.long, device=device)
    else:
        attn = attn.to(device)
        
    # === Before entering the generation loop, clip max_new_tokens against the model context limit to avoid overflow ===
    prompt_len = int(input_ids.shape[1])
    try:
        want = int(max_new_tokens or 0)
    except Exception:
        want = 0
    max_new_tokens = _cap_max_new_tokens(prompt_len, want)
    if max_new_tokens <= 0:
        return "", "", prompt_len, 0, prompt_len, [False, False]

    # ====== Prefill stage: prefer KV-copy expansion, and fall back to batch=2 prefill on failure ======
    pkv, last_logits_b2, _used_fallback = _prefill_and_expand_kv(input_ids, attn, times=2)

    # Keep the two branches as independent sequences, while avoiding a duplicated prompt pass on the first step
    cur_ids = input_ids.repeat(2, 1).contiguous()   # [2, L]
    cur_attn = attn.repeat(2, 1).contiguous()       # [2, L]

    # Normalize sampling arguments and reuse HF subcomponents
    do_sample, temperature, top_p = normalize_sampling_args(do_sample, temperature, top_p)
    _, hf_lp, hf_warpers, stopping_criteria = _build_hf_components(
        prompt_len, do_sample, temperature, top_p, max_new_tokens
    )
    # Build processor chains for both branches:
    # Branch 0 (internal-only): HF built-ins + your internal processors
    lp0_full = LogitsProcessorList(list(hf_lp) + list(lp_internal or []))
    # Branch 1 (internal+external): lp0_full plus your external processors
    lp1_full = LogitsProcessorList(list(lp0_full) + list(lp_external or []))

    # Shared RNG, used only for coupled sampling
    gen = None
    if do_sample:
        gen = torch.Generator(device=device)
        if rng_seed is None:
            # Default behavior: derive a stable seed from the input so the same prompt is reproducible
            # Note: this does not expose user content; it only hashes token IDs in a simple way
            seed = int(torch.sum(input_ids).item() % (2**31 - 1))
        else:
            seed = int(rng_seed)
        gen.manual_seed(seed)
    
    # Stop token
    if eos_token_id is None:
        eos_token_id = model.generation_config.eos_token_id
    eos_ids: List[int] = []
    if isinstance(eos_token_id, int) and eos_token_id >= 0:
        eos_ids = [eos_token_id]
    elif isinstance(eos_token_id, (list, tuple)):
        eos_ids = [int(x) for x in eos_token_id if x is not None]

    finished = [False, False]
    # Exact count of effective generated tokens on each branch, excluding alignment copies
    comp_tok_each = [0, 0]
    new_steps = 0  # Number of synchronized steps across both branches

    def _apply(proc: Optional[LogitsProcessorList], ids_ctx: torch.Tensor, scores: torch.Tensor) -> torch.Tensor:
        # ids_ctx: [1, seq], scores: [1, vocab]
        if proc is not None:
            scores = proc(ids_ctx, scores)
        return scores

    # ====== First generation step: internal-only vs. internal-plus-external with coupled sampling ======
    logits_b2 = last_logits_b2  # [2, vocab]
    base0 = _apply(lp0_full, cur_ids[0:1, :], logits_b2[0:1, :])  # [1, vocab]
    base1 = _apply(lp1_full, cur_ids[1:2, :], logits_b2[1:2, :])  # [1, vocab]
    # Branch 0: internal_only
    scores0 = base0.clone()
    # Branch 1: internal_plus_external
    scores1 = base1.clone()
    # Shared warper path, reusing HF warpers
    if do_sample and len(hf_warpers):
        scores0 = hf_warpers(cur_ids[0:1, :], scores0)
        scores1 = hf_warpers(cur_ids[1:2, :], scores1)
    # Coupled sampling using the same shared u
    tok0, tok1 = _coupled_pick_from_scores(scores0, scores1, do_sample, generator=gen)
    # Update counts and stop flags
    comp_tok_each[0] += (not finished[0])
    comp_tok_each[1] += (not finished[1])
    if eos_ids and int(tok0.item()) in eos_ids:
        finished[0] = True
    if eos_ids and int(tok1.item()) in eos_ids:
        finished[1] = True

    # Concatenate and align
    next_ids = torch.cat([tok0, tok1], dim=0)  # [2,1]
    cur_ids = torch.cat([cur_ids, next_ids], dim=1)
    cur_attn = torch.cat([cur_attn, torch.ones((2, 1), dtype=cur_attn.dtype, device=device)], dim=1)
    new_steps = 1
    # Check HF stopping criteria, including length
    if stopping_criteria(cur_ids, None):
        # If the maximum length is reached, exit immediately; finish_reason will be determined at return time using finished[] and length
        texts = tokenizer.batch_decode(cur_ids[:, prompt_len:], skip_special_tokens=True)
        prompt_tok = int(inputs["input_ids"].shape[1])
        comp_tok_sum = int(comp_tok_each[0] + comp_tok_each[1])
        total_tok = prompt_tok + comp_tok_sum
        return texts[0], texts[1], prompt_tok, comp_tok_sum, total_tok, finished

    # ====== Incremental decoding for later steps: one batch=2 forward pass per newest token ======
    while new_steps < max_new_tokens:
        # Stop condition: exit only after both branches have finished and min_new_tokens has been satisfied
        if all(finished) and new_steps >= min_new_tokens:
            break

        step_in = cur_ids[:, -1:].contiguous()  # [2,1]
        outputs = model(
            input_ids=step_in,
            attention_mask=cur_attn,
            past_key_values=pkv,
            use_cache=True
        )
        pkv = outputs.past_key_values
        logits = outputs.logits[:, -1, :]   # [2, vocab]

        # Compute the internal baseline distribution at this step for each branch using its own context
        base0 = _apply(lp0_full, cur_ids[0:1, :], logits[0:1, :])   # [1, vocab]
        base1 = _apply(lp1_full, cur_ids[1:2, :], logits[1:2, :])   # [1, vocab]

        active0 = not finished[0]
        active1 = not finished[1]

        scores0 = None
        scores1 = None
        if active0:
            scores0 = base0.clone()
            if do_sample and len(hf_warpers):
                scores0 = hf_warpers(cur_ids[0:1, :], scores0)
        if active1:
            scores1 = base1.clone()
            if do_sample and len(hf_warpers):
                scores1 = hf_warpers(cur_ids[1:2, :], scores1)

        # Unified decision logic: four cases
        if active0 and active1:
            tok0, tok1 = _coupled_pick_from_scores(scores0, scores1, do_sample, generator=gen)
        elif active0 and (not active1):
            # Only branch 0 continues: use self-coupled sampling and freeze branch 1
            tok0, _ = _coupled_pick_from_scores(scores0, scores0, do_sample, generator=gen)
            tok1 = cur_ids[1:2, -1:].clone()
        elif (not active0) and active1:
            # Only branch 1 continues: use self-coupled sampling and freeze branch 0
            tok1, _ = _coupled_pick_from_scores(scores1, scores1, do_sample, generator=gen)
            tok0 = cur_ids[0:1, -1:].clone()
        else:
            # Both branches have finished: keep the last token for alignment concatenation
            tok0 = cur_ids[0:1, -1:].clone()
            tok1 = cur_ids[1:2, -1:].clone()

        # Record effective generated tokens and stop flags
        if active0:
            comp_tok_each[0] += 1
            if eos_ids and int(tok0.item()) in eos_ids:
                finished[0] = True
        if active1:
            comp_tok_each[1] += 1
            if eos_ids and int(tok1.item()) in eos_ids:
                finished[1] = True

        # Concatenate
        next_ids = torch.cat([tok0, tok1], dim=0)  # [2,1]
        cur_ids = torch.cat([cur_ids, next_ids], dim=1)
        cur_attn = torch.cat([cur_attn, torch.ones((2,1), dtype=cur_attn.dtype, device=device)], dim=1)

        new_steps += 1
        # Check HF stopping criteria, including length
        if stopping_criteria(cur_ids, None):
            break


    texts = tokenizer.batch_decode(cur_ids[:, prompt_len:], skip_special_tokens=True)
    # Compute token counts
    prompt_tok = int(inputs["input_ids"].shape[1])
    comp_tok_sum = int(comp_tok_each[0] + comp_tok_each[1])  # Sum of effective completion tokens across both parallel branches
    total_tok = prompt_tok + comp_tok_sum
    
    return texts[0], texts[1], prompt_tok, comp_tok_sum, total_tok, finished

@app.post("/v1/chat/completions")
async def chat(req: ChatRequest) -> Dict[str, Any]:
    print(f"[recv] at {time.time():.3f} messages={len(req.messages)} parallel={req.parallel}")
    import sys; sys.stdout.flush()
    # Basic validation: messages must not be empty
    if not req.messages:
        raise HTTPException(status_code=422, detail="messages must not be empty")
    msgs = [m.model_dump() for m in req.messages]
    inputs = _prep_inputs(msgs)
    # Extra validation: prompt length must not exceed the context limit; otherwise return 400 immediately
    try:
        prompt_len = int(inputs["input_ids"].shape[1])
    except Exception:
        prompt_len = 0
    ctx_lim = _model_ctx_limit()
    if isinstance(ctx_lim, int) and prompt_len > ctx_lim:
        raise HTTPException(status_code=400, detail=f"prompt_too_long: {prompt_len}>{ctx_lim}")

    # Parallel mode: two branches, internal-only and internal-plus-external
    if req.parallel:
        # Optional validation: whether parallel mode must provide an external chain, controlled via environment variable
        if REQUIRE_EXTERNAL_IN_PARALLEL and not req.external_processor_names:
            raise HTTPException(status_code=400, detail="parallel=True requires an external_processor_names list (this restriction can be disabled with REQUIRE_EXTERNAL_IN_PARALLEL=0)")

        # Build the internal-only chain as the baseline, and the external-only chain to be applied on top of it
        lp_internal = _resolve_lp_list(
            internal_names=req.internal_processor_names,
            external_names=None,
            mode="internal_only"
        )
        lp_external = _resolve_lp_list(   # External-only chain; None is allowed
            internal_names=None,
            external_names=req.external_processor_names,
            mode="any",
            external_params=req.external_processor_params
        )

        try:
            # Run in a thread pool to avoid blocking the event loop, and explicitly handle CUDA OOM
            text_internal, text_both, prompt_tok, comp_tok_sum, total_tok, finished = await asyncio.to_thread(
                _dual_sync_generate_internal_base,
                inputs,
                lp_internal,
                lp_external,
                req.temperature,
                req.top_p,
                req.max_tokens,
                model.generation_config.eos_token_id,
                0,
                do_sample=req._do_sample,
                rng_seed=req.rng_seed,
            )
        except torch.cuda.OutOfMemoryError as e:
            try:
                torch.cuda.empty_cache()
            except Exception:
                pass
            raise HTTPException(status_code=503, detail="generation_error: cuda_oom") from e
        except Exception as e:
            # Normalize all remaining exceptions into 500 responses to avoid exposing stack traces
            raise HTTPException(status_code=500, detail=f"generation_error: {e.__class__.__name__}: {e}") from e
        
        # Set finish_reason precisely per branch: EOS -> "stop"; reaching the length cap -> "length"
        fr_internal = "stop" if finished[0] else "length"
        fr_both = "stop" if finished[1] else "length"

        return {
            "id": f"chatcmpl-{int(time.time()*1000)}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": req.model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": text_internal},
                    "finish_reason": fr_internal,
                    "variant": "internal_only"
                },
                {
                    "index": 1,
                    "message": {"role": "assistant", "content": text_both},
                    "finish_reason": fr_both,
                    "variant": "internal_plus_external"
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tok,
                "completion_tokens": comp_tok_sum,
                "total_tokens": total_tok
            }
        }

    # Non-parallel mode: build the chain from the provided lists, which may be internal-only, external-only, or mixed
    # To guarantee that "single branch == parallel internal-only path", only your internal chain is applied here,
    # while reusing the same HF subcomponents instead of calling model.generate directly.
    lp_internal_only = _resolve_lp_list(
        internal_names=req.internal_processor_names,
        external_names=None,
        mode="internal_only",
    )
    try:
        text, prompt_tok, comp_tok, total_tok = await asyncio.to_thread(
            _gen_internal_like_parallel,
            inputs,
            lp_internal_only,
            req.temperature,
            req.top_p,
            req.max_tokens,
            do_sample=req._do_sample,
            rng_seed=req.rng_seed,
        )
    except torch.cuda.OutOfMemoryError as e:
        try:
            torch.cuda.empty_cache()
        except Exception:
            pass
        raise HTTPException(status_code=503, detail="generation_error: cuda_oom") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"generation_error: {e.__class__.__name__}: {e}") from e
    # More accurate finish_reason, based on comparison with the clipped max_new_tokens
    try:
        prompt_len = int(inputs["input_ids"].shape[1])
        want = int(req.max_tokens or 0)
    except Exception:
        prompt_len, want = int(inputs["input_ids"].shape[1]), 0
    capped = _cap_max_new_tokens(prompt_len, want)
    # comp_tok == capped means the length cap was reached; otherwise treat it as a normal stop
    fr = "length" if capped > 0 and comp_tok >= capped else "stop"
    return {
        "id": f"chatcmpl-{int(time.time()*1000)}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model,
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": fr}
        ],
        "usage": {
            "prompt_tokens": prompt_tok,
            "completion_tokens": comp_tok,
            "total_tokens": total_tok
        }
    }

# Start with sampling enabled: `uvicorn server:app --host 0.0.0.0 --port 8000`
# Start with sampling disabled: `SERVER_DO_SAMPLE=0 uvicorn server:app --host 0.0.0.0 --port 8000`
# Optional environment parameters:
##SAMPLING_MODE=lenient_openai | map_to_greedy | strict
# See normalize_sampling_args() for details. Default: lenient_openai.
# Note: if you use "strict" mode,
# then passing temperature<=0 in the request body will raise an error.
##SERVER_DO_SAMPLE=0 | 1 | false | true
# This parameter determines the default sampling mode; sampling is enabled by default (true).
# You can also specify sampling behavior per request in the request body.
