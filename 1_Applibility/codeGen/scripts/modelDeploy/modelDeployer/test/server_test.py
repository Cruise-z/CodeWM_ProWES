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

# ================= Configuration options (sampling toggle / parallel identical configs) =================
import os
# SERVER_DO_SAMPLE: "1"/"true" enables sampling; "0"/"false" uses greedy decoding. Default is enabled.
def _as_bool(x: str) -> bool:
    return str(x).strip().lower() not in ("0", "false", "no", "off", "")
SERVER_DO_SAMPLE = _as_bool(os.getenv("SERVER_DO_SAMPLE", "1"))
# SAMPLING_MODE: "lenient_openai" | "map_to_greedy" | "strict"
# See normalize_sampling_args() for details. Default is "lenient_openai".
def _as_mode(x: str) -> str:
    """Normalize the string to one of {'lenient_openai','map_to_greedy','strict'}."""
    s = str(x or "").strip().lower().replace("-", "_")
    if s in ("lenient_openai", "lenient", "openai", "lo"):
        return "lenient_openai"
    if s in ("map_to_greedy", "map2greedy", "to_greedy", "greedy_map", "mg"):
        return "map_to_greedy"
    if s in ("strict", "error", "raise", "s"):
        return "strict"
    # If unknown, fall back to lenient mode
    return "lenient_openai"
SAMPLING_MODE = _as_mode(os.getenv("SAMPLING_MODE", "lenient_openai"))

# Whether to require external_processor_names in parallel mode (avoid the misuse of "two routes same config")
REQUIRE_EXTERNAL_IN_PARALLEL = _as_bool(os.getenv("REQUIRE_EXTERNAL_IN_PARALLEL", "0"))

# ====== Raw request body logging control (off by default, enable if needed) ======
# LOG_REQ_BODY=1 enables logging; LOG_REQ_BODY_BYTES controls the maximum raw bytes logged
LOG_REQ_BODY = _as_bool(os.getenv("LOG_REQ_BODY", "0"))
LOG_REQ_BODY_BYTES = int(os.getenv("LOG_REQ_BODY_BYTES", "4096"))

# ================= Model loading (no built-in watermark enabled by default) =================
MODEL_ID = "Qwen/Qwen2.5-Coder-32B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID, torch_dtype=torch.bfloat16, device_map="cuda"
)
model.eval()
# === Tokenizer/model configuration fallback before generation: avoid missing pad tokens, warnings, or out-of-range issues ===
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
    # Fallback should not affect the main flow; ignore silently
    pass

# Vocabulary IDs for your processor construction (exactly aligned with this service tokenizer)
vocab_ids: List[int] = list(tokenizer.get_vocab().values())

# ================= Processor registry & registration functions =================
# You can register HF built-in watermark or your custom watermark on either side as you prefer
# Register factory functions, instantiate during request parsing to avoid sharing mutable state across requests
ProcessorFactory = Callable[[], LogitsProcessorList]
INTERNAL_PROCESSORS: Dict[str, ProcessorFactory] = {}
EXTERNAL_PROCESSORS: Dict[str, ProcessorFactory] = {} # Type and API preserved for compatibility, but not used during parsing

# ===== Fully builder-based: external processors are instantiated dynamically through parameterized builders =====
ParametricBuilder = Callable[..., Any]
EXTERNAL_BUILDERS: Dict[str, ParametricBuilder] = {}

def register_external_builder(name: str, builder: ParametricBuilder) -> None:
    """
    Register a parameterized external processor builder. The request can pass parameters via external_processor_params[name];
    vocab=vocab_ids is enforced here, ignoring any provided vocab.
    """
    if not callable(builder):
        raise TypeError(f"external builder for '{name}' must be callable")
    EXTERNAL_BUILDERS[name] = builder

def _ensure_lp_list(p) -> LogitsProcessorList:
    """
    Normalize the object to a LogitsProcessorList and enforce strong type checking:
      - None is not allowed
      - Allowed types: single LogitsProcessor, LogitsProcessorList, or list/tuple[LogitsProcessor]
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
    Normalize to a zero-argument factory function:
      1) If the object is a processor instance (even if callable, treat it as an instance) → return a clone each time;
      2) Otherwise, if it is a callable zero-arg factory → call it and enforce strict type checking;
    """
    # ✅ Prefer handling processor instances first (LogitsProcessor / LogitsProcessorList / list/tuple[LogitsProcessor])
    if isinstance(factory_or_obj, (LogitsProcessor, LogitsProcessorList, list, tuple)):
        inst_lp = _ensure_lp_list(factory_or_obj)
        def _factory_from_instance() -> LogitsProcessorList:
            return _clone_lp_list(inst_lp)
        return _factory_from_instance
    # ✅ Next, treat callable objects as zero-arg factories
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
    """Register into the built-in processor namespace (stored as a factory)."""
    INTERNAL_PROCESSORS[name] = _as_factory(factory_or_obj)

def register_external(name: str, factory_or_obj: Any) -> None:
    """
    Compatibility function: preserved for legacy calls, but EXTERNAL_PROCESSORS is not used during parsing.
    If still called, this function only registers and does not participate in the generation path.
    """
    EXTERNAL_PROCESSORS[name] = _as_factory(factory_or_obj)

def _clone_lp_list(lp: LogitsProcessorList) -> LogitsProcessorList:
    """
    Clone processor instances per request to avoid cross-request or dual-path state leakage.
    If deepcopy fails, fall back to the original object without interrupting execution.
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
    """Compose a LogitsProcessorList from named processors while preserving the input order.
       Convention: in parallel mode, internal processors come before external; the same ordering applies in single-path mode.
    """
    chain: List[Any] = []

    if internal_names:
        for n in internal_names:
            if n not in INTERNAL_PROCESSORS:
                raise HTTPException(status_code=400, detail=f"Unknown internal processor: {n}")
            # Instantiate the factory -> get an independent processor chain for this request
            try:
                lp = INTERNAL_PROCESSORS[n]()
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Internal processor '{n}' factory error: {e}") from e
            # Perform strong type checking on each item
            for it in lp:
                if not isinstance(it, LogitsProcessor):
                    raise HTTPException(status_code=400, detail=f"Internal processor '{n}' produced invalid item: {type(it)}")
            chain.extend(lp)

    if mode != "internal_only" and external_names:
        for n in external_names:
            if n not in EXTERNAL_BUILDERS:
                # Pure builder mode: unregistered builder raises directly
                raise HTTPException(status_code=400, detail=f"Unknown external builder: {n}")
            # Extract parameters from the request and enforce vocab override
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

# ===== Insert here: auto-load uiAPI (optional) =====
try:
    import importlib, sys, os
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    importlib.import_module("regWM")  # register_xxx should be called at module import time
    print("[server] processors loaded ->",
          "internal:", list(INTERNAL_PROCESSORS.keys()),
          "external_builders:", list(EXTERNAL_BUILDERS.keys()))
except Exception as e:
    print(f"[server] regWM not loaded: {e}")

# ================== OpenAI compatible request/response model ==================
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: Optional[str] = MODEL_ID
    messages: List[Message]
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.95
    max_tokens: Optional[int] = 512
    stream: Optional[bool] = False  # This example does not use streaming
    # Optional: fix the request RNG seed for reproducibility; if omitted, it can still be coupled
    rng_seed: Optional[int] = None

    # The processor lists you care about (all are lists) — names must already be registered
    internal_processor_names: Optional[List[str]] = None
    external_processor_names: Optional[List[str]] = None

    # Parallel toggle: True returns two branches (internal-only and internal+external)
    parallel: Optional[bool] = False
    # Only applies to external processors: pass builder parameters by name
    external_processor_params: Optional[Dict[str, Dict[str, Any]]] = None
    
    # Hidden switch: not exposed in schema and cannot be provided by clients
    _do_sample: bool = PrivateAttr(default=SERVER_DO_SAMPLE)

# Normalize incoming request parameters
def normalize_sampling_args(do_sample: bool,
                            temperature: Optional[float],
                            top_p: Optional[float],
                            mode: str = SAMPLING_MODE):
    """
    mode:
      - "lenient_openai": when do_sample=True and temp<=0 -> temp=1e-4; when do_sample=False -> temp=1.0, top_p=1.0
      - "map_to_greedy": when do_sample=True and temp<=0 -> do_sample=False (convert to greedy)
      - "strict":         when do_sample=True and temp<=0 -> raise ValueError
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

# ====== Simple request body size logging middleware (enabled only for specific routes) ======
logger = logging.getLogger("server")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

class LogReqSizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # The tracked routes may be adjusted as needed
        if request.url.path in ("/v1/chat/completions", "/dbg/echo-len"):
            try:
                body = await request.body()          # Starlette caches the body so it can be read again
                size = len(body or b"")
                cl = request.headers.get("content-length")
                # Try to parse the parallel field for debugging parallel stress tests
                parallel = None
                try:
                    data = json.loads(body.decode("utf-8"))
                    parallel = data.get("parallel", None)
                except Exception:
                    pass
                logger.info("[recv] bytes=%s content-length=%s path=%s parallel=%s",
                            size, cl, request.url.path, parallel)
                # Optional: log the request payload content (subject to LOG_REQ_BODY / LOG_REQ_BODY_BYTES)
                if LOG_REQ_BODY:
                    preview = body[:LOG_REQ_BODY_BYTES]
                    # Try JSON pretty-print first; fall back to plain text on failure
                    printed = None
                    try:
                        parsed = json.loads(preview.decode("utf-8", "replace"))
                        printed = json.dumps(parsed, ensure_ascii=False, indent=2)
                    except Exception:
                        printed = preview.decode("utf-8", "replace")
                    # Mark preview size versus total size to avoid implying this is the full body
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
    """Debug endpoint: list currently registered processor names."""
    return {
        "internal": list(INTERNAL_PROCESSORS.keys()),
        "external": list(EXTERNAL_PROCESSORS.keys()),     # preserved for compatibility display
        "external_builders": list(EXTERNAL_BUILDERS.keys())
    }
    
@app.get("/v1/models")
def list_models():
    """OpenAI compatible endpoint: list a single available model."""
    return {"object": "list", "data": [{"id": MODEL_ID, "object": "model"}]}

# ====== Debug endpoint: return the request body length ======
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
    Infer the model's maximum supported context length in tokens. Different models/configurations use different field names,
    so this provides compatibility fallback logic. If rope_scaling exists (e.g. Llama/Qwen extensions), it estimates the effective limit by factor.
    Returns None if the limit cannot be determined reliably.
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

def _cap_max_new_tokens(prompt_len: int, want_new: Optional[int]) -> int:
    ctx = _model_ctx_limit()
    safe = int(want_new or 0)
    return max(0, min(safe, (ctx - prompt_len) if isinstance(ctx, int) else safe))

@app.get("/healthz")
def healthz():
    """Simple health check endpoint; useful for load balancer probing."""
    return {"status": "ok", "model": MODEL_ID}

def _is_cache_obj(pkv) -> bool:
    """
    Detect whether the object is a transformers new-style Cache object (e.g. StaticCache/DynamicCache).
    These objects often provide get_seq_length()/get_max_capacity methods.
    """
    if pkv is None:
        return False
    cls_name = pkv.__class__.__name__.lower()
    return hasattr(pkv, "get_seq_length") or cls_name.endswith("cache")
    
def _prefill_and_expand_kv(input_ids: torch.Tensor,
                           attn: torch.Tensor,
                           times: int = 2):
    """
    Do one batch=1 prefill and attempt to replicate past_key_values across the batch dimension.
    If replication fails (for example due to new-style Cache abstractions or non-tensor structures),
    fall back to a batch=times prefill (recomputing the prompt once, but ensuring compatibility).
    Returns: (pkv_batched, last_logits_batched[times, vocab], used_fallback: bool)
    """
    prefill = model(input_ids=input_ids, attention_mask=attn, use_cache=True)
    pkv = prefill.past_key_values
    last_logits_1 = prefill.logits[:, -1, :]  # [1, vocab]
    # New-style Cache: do not replicate it; fall back to a batch=times prefill instead (more stable and consistent with model expectations)
    if _is_cache_obj(pkv):
        ids2 = input_ids.repeat(times, 1).contiguous()
        attn2 = attn.repeat(times, 1).contiguous()
        prefill2 = model(input_ids=ids2, attention_mask=attn2, use_cache=True)
        pkv2 = prefill2.past_key_values
        last_logits_batched = prefill2.logits[:, -1, :]  # [times, vocab]
        return pkv2, last_logits_batched, True

    # Legacy tuple/list: attempt to replicate KV across the batch dimension
    try:
        pkv_batched = _repeat_pkv(pkv, times=times)
        last_logits_batched = last_logits_1.repeat(times, 1)
        return pkv_batched, last_logits_batched, False
    except Exception:
        # Final fallback: perform a batch=times prefill
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
    Replicate single-stream past_key_values along the batch dimension.
    Compatible with most HF pkv structures: tuple[layer] -> tuple[tensor...]
    """
    if pkv is None:
        return None
    # Only allow replication for legacy tuple/list structures; new-style Cache raises and triggers fallback logic
    if not isinstance(pkv, (tuple, list)):
        raise TypeError(f"repeat_pkv expects legacy tuple/list, got {type(pkv)}")
    rep_layers = []
    # Some implementations return list; normalize by iterating over layers
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
    Compatibly obtain HF logits_processor; fall back to an empty list if the model lacks the private method.
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
    Compatibly obtain HF warpers; if the model lacks the private method, construct them manually from temperature / top_p.
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
            # Add TopKLogitsWarper here if top_k support is required
        return warpers

def _safe_get_stopping_criteria(gen_cfg) -> StoppingCriteriaList:
    """
    Compatibly obtain HF stopping_criteria; return an empty list if the model lacks the private method.
    """
    try:
        return model._get_stopping_criteria(gen_cfg, None)
    except Exception:
        return StoppingCriteriaList([])
    
def _stopping_met(stopping_criteria: StoppingCriteriaList,
                  input_ids: torch.Tensor,
                  scores: Optional[torch.Tensor] = None) -> bool:
    """
    Normalize the return value of StoppingCriteriaList to bool.
    - Standard implementations return bool;
    - If a custom criterion returns a BoolTensor with shape=[B], reduce with any();
    - Other truthy objects are converted with bool().
    On error, safely treat it as not triggered.
    """
    try:
        out = stopping_criteria(input_ids, scores)
        if isinstance(out, bool):
            return out
        if torch.is_tensor(out):
            # Support both 0-d and 1-d (batch dimension) tensor shapes
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
    Reuse HF generation submodules: construct from normalized sampling configuration
    - hf_logits_processor: HF built-in processors (e.g. no_repeat_ngram/repetition_penalty/...)
    - hf_warpers: HF built-in warpers (temperature/top_p/top_k/...)
    - stopping_criteria: HF stopping criteria (ensure MaxLengthCriteria(prompt_len+max_new_tokens))
    """
    # Clone the generation config to avoid mutating global state
    gen_cfg = copy.deepcopy(model.generation_config)
    gen_cfg.do_sample = bool(do_sample)
    if temperature is not None:
        gen_cfg.temperature = float(temperature)
    if top_p is not None:
        gen_cfg.top_p = float(top_p)
    # Allow the stopping criteria to derive max_length semantics from max_new_tokens
    # Note: HF typically combines max_new_tokens with current length into max_length; explicitly fill it here.
    max_len = int(prompt_len + max_new_tokens) if max_new_tokens and max_new_tokens > 0 else int(prompt_len)

    # Note: HF private methods may be absent on some models, so provide a safe fallback
    hf_lp = _safe_get_logits_processor(gen_cfg, prompt_len)
    hf_warpers = _safe_get_logits_warper(gen_cfg)
    stopping_criteria = _safe_get_stopping_criteria(gen_cfg)
    # If MaxLengthCriteria is absent, append one with max prompt_len+max_new_tokens
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
    Generate a single path that is fully aligned with the parallel "internal-only" branch:
      - share the same HF submodules (hf_logits_processor + hf_warpers)
      - step and terminate the same way as parallel mode (incremental forward step-by-step)
      - sample using the same U(0,1) CDF method as parallel mode (via coupled sampling)
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

    # Normalize sampling arguments and build HF submodules accordingly
    do_sample, temperature, top_p = normalize_sampling_args(do_sample, temperature, top_p)
    _, hf_lp, hf_warpers, stopping_criteria = _build_hf_components(
        prompt_len, do_sample, temperature, top_p, max_new_tokens
    )
    lp0_full = LogitsProcessorList(list(hf_lp) + list(lp_internal or []))

    # Share the random source (seed derivation matches parallel mode)
    gen = None
    if do_sample:
        gen = torch.Generator(device=device)
        seed = int(torch.sum(input_ids).item() % (2**31 - 1)) if rng_seed is None else int(rng_seed)
        gen.manual_seed(seed)

    # Prefill
    pkv, last_logits_b1, _ = _prefill_and_expand_kv(input_ids, attn, times=1)
    cur_ids = input_ids.clone()
    cur_attn = attn.clone()

    # Termination token
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

    # First step: use the final logits from prefill
    scores0 = _apply(lp0_full, cur_ids, last_logits_b1)  # [1,V]
    if do_sample and len(hf_warpers):
        scores0 = hf_warpers(cur_ids, scores0)
    # Coupled sampling (ensures the same sampling distribution/numeric path as parallel internal-only)
    tok0, _ = _coupled_pick_from_scores(scores0, scores0, do_sample, generator=gen)
    comp_tok += 1
    if eos_ids and int(tok0.item()) in eos_ids:
        finished = True
    cur_ids = torch.cat([cur_ids, tok0], dim=1)
    cur_attn = torch.cat([cur_attn, torch.ones((1,1), dtype=cur_attn.dtype, device=device)], dim=1)
    # HF stopping criteria (length, etc.) check
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
        # HF stopping criteria (length, etc.) check
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
    Coupled sampling with a shared random number:
      - do_sample=False: both paths argmax (fully consistent deterministic rule)
      - do_sample=True: sample a common u ~ U(0,1) and use the same u on each CDF
    Input shapes: scoresX [1, vocab], returns token ids with shape [1,1]
    """
    if not do_sample:
        tok0 = scores0.argmax(dim=-1, keepdim=True)
        tok1 = scores1.argmax(dim=-1, keepdim=True)
        return tok0, tok1
    # softmax -> probabilities; note float32 numerical stability
    p0 = torch.softmax(scores0, dim=-1).to(torch.float32)  # [1,V]
    p1 = torch.softmax(scores1, dim=-1).to(torch.float32)  # [1,V]
    # Shared random number u
    if generator is None:
        u = torch.rand((), device=scores0.device)
    else:
        u = torch.rand((), device=scores0.device, generator=generator)
    # Numerical safety: prevent u==1 from causing an out-of-range index
    eps = torch.finfo(p0.dtype).eps
    u = torch.clamp(u, eps, 1 - eps)
    # CDF search
    cdf0 = p0.cumsum(dim=-1).squeeze(0)  # [V]
    cdf1 = p1.cumsum(dim=-1).squeeze(0)  # [V]
    # Boundary protection: in extreme numeric cases the cdf tail may be < 1 and searchsorted may return V
    i0 = torch.searchsorted(cdf0, u).clamp(max=cdf0.numel() - 1).long().item()
    i1 = torch.searchsorted(cdf1, u).clamp(max=cdf1.numel() - 1).long().item()
    return (torch.tensor([[i0]], device=scores0.device, dtype=torch.long),
            torch.tensor([[i1]], device=scores1.device, dtype=torch.long))

@torch.inference_mode()
def _dual_sync_generate_internal_base(
    inputs: Dict[str, torch.Tensor],
    lp_internal: Optional[LogitsProcessorList],   # internal-only chain
    lp_external: Optional[LogitsProcessorList],   # external-only chain (may be None)
    temperature: float,
    top_p: float,
    max_new_tokens: int,
    eos_token_id: Optional[Union[int, List[int]]] = None,
    min_new_tokens: int = 0,
    do_sample: bool = SERVER_DO_SAMPLE,           # new option, defaults to global setting
    rng_seed: Optional[int] = None,
) -> tuple[str, str, int, int, int, List[bool]]:
    """
    Synchronous forked parallel generation using the internal-processed distribution as the baseline, while avoiding duplicate prompt forwards:
    - perform one forward pass per step to obtain logits;
    - scores_internal = internal processor chain(logits) as the baseline distribution;
      * internal_only branch: sample on scores_internal;
      * internal_plus_external branch: clone scores_internal and apply the external chain before sampling.
    - both paths advance their own sequences (batch=2, shared KV cache).
    Returns: (text_internal_only, text_internal_plus_external, prompt_tok, completion_tok_sum, total_tok, finished[List[bool]])
    """
    device = next(model.parameters()).device
    input_ids = inputs["input_ids"].to(device)  # [1, L]
    attn = inputs.get("attention_mask", None)
    if attn is None:
        attn = torch.ones_like(input_ids, dtype=torch.long, device=device)
    else:
        attn = attn.to(device)
        
    # === Before entering the generation loop, clip max_new_tokens to the model context limit to avoid overflow ===
    prompt_len = int(input_ids.shape[1])
    try:
        want = int(max_new_tokens or 0)
    except Exception:
        want = 0
    max_new_tokens = _cap_max_new_tokens(prompt_len, want)
    if max_new_tokens <= 0:
        return "", "", prompt_len, 0, prompt_len, [False, False]

    # ====== Prefill stage: attempt KV replication first, fallback to batch=2 prefill if needed ======
    pkv, last_logits_b2, _used_fallback = _prefill_and_expand_kv(input_ids, attn, times=2)

    # Both paths keep independent sequences, but avoid re-running the prompt for the first step
    cur_ids = input_ids.repeat(2, 1).contiguous()   # [2, L]
    cur_attn = attn.repeat(2, 1).contiguous()       # [2, L]

    # Normalize sampling parameters and reuse HF submodules
    do_sample, temperature, top_p = normalize_sampling_args(do_sample, temperature, top_p)
    _, hf_lp, hf_warpers, stopping_criteria = _build_hf_components(
        prompt_len, do_sample, temperature, top_p, max_new_tokens
    )
    # Build processor chains for both paths:
    # path 0 (internal-only): HF built-ins + your internal processors
    lp0_full = LogitsProcessorList(list(hf_lp) + list(lp_internal or []))
    # path 1 (internal+external): extend lp0_full with your external processors
    lp1_full = LogitsProcessorList(list(lp0_full) + list(lp_external or []))

    # Shared random number generator (used only for coupled sampling)
    gen = None
    if do_sample:
        gen = torch.Generator(device=device)
        if rng_seed is None:
            # Default: construct a stable seed from the input (same prompt is reproducible)
            # Note: does not leak user content, only hashes token ids
            seed = int(torch.sum(input_ids).item() % (2**31 - 1))
        else:
            seed = int(rng_seed)
        gen.manual_seed(seed)
    
    # Termination token
    if eos_token_id is None:
        eos_token_id = model.generation_config.eos_token_id
    eos_ids: List[int] = []
    if isinstance(eos_token_id, int) and eos_token_id >= 0:
        eos_ids = [eos_token_id]
    elif isinstance(eos_token_id, (list, tuple)):
        eos_ids = [int(x) for x in eos_token_id if x is not None]

    finished = [False, False]
    # Accurate per-path completion token counts (excluding alignment copies)
    comp_tok_each = [0, 0]
    new_steps = 0  # number of aligned steps across both paths

    def _apply(proc: Optional[LogitsProcessorList], ids_ctx: torch.Tensor, scores: torch.Tensor) -> torch.Tensor:
        # ids_ctx: [1, seq], scores: [1, vocab]
        if proc is not None:
            scores = proc(ids_ctx, scores)
        return scores

    # ====== First-step generation (direct comparison: internal vs internal+external; coupled sampling) =====
    logits_b2 = last_logits_b2  # [2, vocab]
    base0 = _apply(lp0_full, cur_ids[0:1, :], logits_b2[0:1, :])  # [1, vocab]
    base1 = _apply(lp1_full, cur_ids[1:2, :], logits_b2[1:2, :])  # [1, vocab]
    # Path 0: internal_only
    scores0 = base0.clone()
    # Path 1: internal_plus_external
    scores1 = base1.clone()
    # Apply the same warper to both paths (reusing HF warpers)
    if do_sample and len(hf_warpers):
        scores0 = hf_warpers(cur_ids[0:1, :], scores0)
        scores1 = hf_warpers(cur_ids[1:2, :], scores1)
    # —— Coupled sampling (shared u) ——
    tok0, tok1 = _coupled_pick_from_scores(scores0, scores1, do_sample, generator=gen)
    # Count and termination
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
    # HF stopping criteria (length, etc.) check
    if stopping_criteria(cur_ids, None):
        # If the length limit is reached, exit immediately; finish_reason will be set later based on finished[] and length
        texts = tokenizer.batch_decode(cur_ids[:, prompt_len:], skip_special_tokens=True)
        prompt_tok = int(inputs["input_ids"].shape[1])
        comp_tok_sum = int(comp_tok_each[0] + comp_tok_each[1])
        total_tok = prompt_tok + comp_tok_sum
        return texts[0], texts[1], prompt_tok, comp_tok_sum, total_tok, finished

    # ====== Subsequent incremental decoding: one batch=2 forward per new token ======
    while new_steps < max_new_tokens:
        # Termination check (exit only after both paths have finished and min_new_tokens is satisfied)
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

        # Compute the internal baseline distribution for each path's own context at this step
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

        # Unified decision making: four cases
        if active0 and active1:
            tok0, tok1 = _coupled_pick_from_scores(scores0, scores1, do_sample, generator=gen)
        elif active0 and (not active1):
            # Only path 0 continues: use coupled sampling while path 1 freezes
            tok0, _ = _coupled_pick_from_scores(scores0, scores0, do_sample, generator=gen)
            tok1 = cur_ids[1:2, -1:].clone()
        elif (not active0) and active1:
            # Only path 1 continues: use coupled sampling while path 0 freezes
            tok1, _ = _coupled_pick_from_scores(scores1, scores1, do_sample, generator=gen)
            tok0 = cur_ids[0:1, -1:].clone()
        else:
            # Both paths have finished: keep the last token for alignment
            tok0 = cur_ids[0:1, -1:].clone()
            tok1 = cur_ids[1:2, -1:].clone()

        # Record effective generated tokens and completion state
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
        # HF stopping criteria (length, etc.) check
        if stopping_criteria(cur_ids, None):
            break


    texts = tokenizer.batch_decode(cur_ids[:, prompt_len:], skip_special_tokens=True)
    # Compute token counts
    prompt_tok = int(inputs["input_ids"].shape[1])
    comp_tok_sum = int(comp_tok_each[0] + comp_tok_each[1])  # sum of effective completion tokens for both parallel paths
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
    # Additional validation: prompt should not exceed the context limit (over-limit returns 400)
    try:
        prompt_len = int(inputs["input_ids"].shape[1])
    except Exception:
        prompt_len = 0
    ctx_lim = _model_ctx_limit()
    if isinstance(ctx_lim, int) and prompt_len > ctx_lim:
        raise HTTPException(status_code=400, detail=f"prompt_too_long: {prompt_len}>{ctx_lim}")

    # Parallel mode: two paths (internal-only and internal+external)
    if req.parallel:
        # Optional validation: require external chain in parallel mode (controlled by env var)
        if REQUIRE_EXTERNAL_IN_PARALLEL and not req.external_processor_names:
            raise HTTPException(status_code=400, detail="parallel=True requires external_processor_names list (set REQUIRE_EXTERNAL_IN_PARALLEL=0 to disable this restriction)")

        # Assemble the internal-only chain (baseline) and the external-only chain (added on top of the baseline)
        lp_internal = _resolve_lp_list(
            internal_names=req.internal_processor_names,
            external_names=None,
            mode="internal_only"
        )
        lp_external = _resolve_lp_list(   # Only take the external chain; allow None
            internal_names=None,
            external_names=req.external_processor_names,
            mode="any",
            external_params=req.external_processor_params
        )

        try:
            # Run in a threadpool to avoid blocking the event loop; handle CUDA OOM explicitly
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
            # Convert all exceptions to 500 to avoid exposing stack traces
            raise HTTPException(status_code=500, detail=f"generation_error: {e.__class__.__name__}: {e}") from e
        
        # Set finish_reason per path precisely: EOS => "stop"; length limit => "length"
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

    # Non-parallel: concatenate processors from your list into one chain (can be internal-only, external-only, or mixed)
    # To ensure single-path equals the parallel internal-only path, only combine your internal chain here and reuse HF submodules,
    # Do not call model.generate directly.
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
    # More accurate finish_reason: compare against capped max_new_tokens
    try:
        prompt_len = int(inputs["input_ids"].shape[1])
        want = int(req.max_tokens or 0)
    except Exception:
        prompt_len, want = int(inputs["input_ids"].shape[1]), 0
    capped = _cap_max_new_tokens(prompt_len, want)
    # comp_tok == capped -> reached length limit; otherwise treat as normal stop
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
# Optional startup parameters:
## SAMPLING_MODE=lenient_openai | map_to_greedy | strict
# See normalize_sampling_args() for details. Default is lenient_openai.
# Note: if you use "strict" mode,
# requests with temperature<=0 will raise an error.
## SERVER_DO_SAMPLE=0 | 1 | false | true
# This setting controls the default sampling mode; sampling is enabled by default (true).
# You can also specify sampling behavior per request in the request body.