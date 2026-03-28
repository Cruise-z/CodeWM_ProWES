# server.py
# pip install "transformers>=4.41" fastapi uvicorn pydantic torch accelerate
import time
import time as _time
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
    LogitsProcessorList,
    LogitsProcessor
)
from transformers.generation.stopping_criteria import (
    StoppingCriteriaList, MaxLengthCriteria
)
import threading

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

# Usage accounting in parallel responses: 1 = each choice has its own usage (default); 0 = legacy merged accounting
USAGE_PER_CHOICE = _as_bool(os.getenv("USAGE_PER_CHOICE", "1"))

# Enable fallback for models that do not support `generator=`; enabled by default
ALLOW_GENERATOR_FALLBACK = _as_bool(os.getenv("ALLOW_GENERATOR_FALLBACK", "1"))

# RNG seed policy (kept consistent with the uploaded documentation): by default, no seed is derived when one is not provided, matching HF behavior;
# to keep compatibility with older behavior, set RNG_SEED_FALLBACK=derived
RNG_SEED_FALLBACK = os.getenv("RNG_SEED_FALLBACK", "none").strip().lower()

# Optional: extreme determinism. Set DETERMINISTIC=1 to enable it, at the cost of performance.
if _as_bool(os.getenv("DETERMINISTIC", "0")):
    try:
        torch.use_deterministic_algorithms(True)
        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":16:8")
        import torch.backends.cudnn as _cudnn
        _cudnn.benchmark = False
        _cudnn.deterministic = True
    except Exception as _e:
        print(f"[server] DETERMINISTIC setup failed: {_e}")

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
# Injected into external builders as the vocab parameter to guarantee a contiguous 0..N-1 id range
# A contiguous id list is used to avoid accidental misuse caused by nondeterministic dict.values() ordering
vocab_ids: List[int] = list(range(len(tokenizer)))

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
       Convention: in parallel mode, internal processors come before external processors; the same "internal first, external second"
       ordering is also used in single-branch mode.
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

_GLOBAL_RNG_LOCK = threading.Lock()

def _pick_seed(rng_seed: Optional[int], input_ids: torch.LongTensor) -> Optional[int]:
    """
    Choose the seed used for this sampling run:
      - If rng_seed is provided, use it directly;
      - Otherwise follow RNG_SEED_FALLBACK:
          * 'derived' -> derive a stable seed from the prompt sum;
          * anything else -> return None, which matches HF default behavior by not passing a generator
    """
    if rng_seed is not None:
        return int(rng_seed)
    if RNG_SEED_FALLBACK == "derived":
        return int(torch.sum(input_ids).item() % (2**31 - 1))
    return None

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

def _prep_inputs(messages: List[Dict[str, str]]) -> Dict[str, torch.Tensor]:
    chat_text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    return tokenizer([chat_text], return_tensors="pt")

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

def _safe_get_stopping_criteria(gen_cfg) -> StoppingCriteriaList:
    """
    Compatibly obtain HF's stopping_criteria; return an empty list if the model lacks the relevant private method.
    """
    try:
        return model._get_stopping_criteria(gen_cfg, None)
    except Exception:
        return StoppingCriteriaList([])

def _fmt_ms(sec: float) -> str:
    """Format seconds as a millisecond string with three decimal places."""
    try:
        return f"{sec * 1000.0:.3f}ms"
    except Exception:
        return f"{sec}s"

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
    stopping_criteria = _safe_get_stopping_criteria(gen_cfg)
    # Add MaxLengthCriteria if it is missing, using prompt_len+max_new_tokens as the cap
    has_maxlen = any(isinstance(c, MaxLengthCriteria) for c in stopping_criteria)
    if not has_maxlen:
        stopping_criteria.append(MaxLengthCriteria(max_length=max_len))
    return gen_cfg, hf_lp, None, stopping_criteria  # warpers are built internally by HF from kwargs

def _count_new_and_reason(seqs: torch.LongTensor,
                          prompt_len: int,
                          capped: int,
                          eos_ids: List[int],
                          pad_id: Optional[int]) -> tuple[List[int], List[str]]:
    """
    Compute generated length and finish_reason ('stop' | 'length') per sample.
    - 'length': reached the capped upper bound
    - 'stop'  : stopped before the cap because EOS or another stopping condition was hit
    """
    B, T = seqs.shape
    new_lens, reasons = [], []
    for b in range(B):
        new_part = seqs[b, prompt_len:]
        # Prefer the first EOS position, including EOS itself, to avoid undercounting by 1 when pad==eos
        new_len = None
        if eos_ids:  # Only search with isin when EOS is actually defined
            eos_tensor = torch.tensor(eos_ids, device=new_part.device, dtype=new_part.dtype)
            # torch.isin: [T] vs [K] -> [T]
            eos_mask = torch.isin(new_part, eos_tensor)
            idx = torch.nonzero(eos_mask, as_tuple=False)
            if idx.numel() > 0:
                first_eos_pos = int(idx[0].item())  # 0-based
                new_len = first_eos_pos + 1         # Include EOS
        if new_len is None:
            # No EOS found: fall back to non-pad counting or full length
            if pad_id is not None:
                new_len = int((new_part != pad_id).sum().item())
            else:
                new_len = int(new_part.numel())
        # Determine finish_reason
        if capped > 0 and new_len >= capped:
            reason = "length"
        else:
           reason = "stop"
        # If the cap was not reached, optionally inspect EOS presence for diagnostics only
        if reason != "length" and eos_ids:
            # If EOS is indeed present, keep 'stop'; otherwise it still remains 'stop' because another criterion may have truncated generation
            pass
        new_lens.append(new_len)
        reasons.append(reason)
    return new_lens, reasons

@torch.inference_mode()
def _hf_generate_single(inputs: Dict[str, torch.Tensor],
                        lp_internal: Optional[LogitsProcessorList],
                        temperature: float,
                        top_p: float,
                        max_new_tokens: int,
                        do_sample: bool,
                        rng_seed: Optional[int]) -> tuple[str, int, int, int, str]:
    device = next(model.parameters()).device
    input_ids = inputs["input_ids"].to(device)
    attn = inputs.get("attention_mask", None)
    if attn is None:
        attn = torch.ones_like(input_ids, dtype=torch.long, device=device)
    else:
        attn = attn.to(device=device, dtype=torch.long)
    prompt_len = int(input_ids.shape[1])
    capped = _cap_max_new_tokens(prompt_len, int(max_new_tokens or 0))
    if capped <= 0:
        # If the user requested a positive value but it was clipped to 0 by the context cap, returning "length" is semantically more accurate
        reason = "length" if int(max_new_tokens or 0) > 0 else "stop"
        return "", prompt_len, 0, prompt_len, reason
    do_sample, temperature, top_p = normalize_sampling_args(do_sample, temperature, top_p)
    _, hf_lp, _, stopping_criteria = _build_hf_components(prompt_len, do_sample, temperature, top_p, capped)
    final_lp = LogitsProcessorList(list(hf_lp) + list(lp_internal or []))
    # Create a private RNG for this call; using the same seed for both branches makes them reproducible without cross-interference
    # Prefer the private-generator path; if the target model does not support it, fall back to the global RNG plus a mutex
    seed_to_use = _pick_seed(rng_seed, input_ids) if do_sample else None
    gen = None
    if do_sample and seed_to_use is not None:
        gen = torch.Generator(device=input_ids.device)
        gen.manual_seed(seed_to_use)

    def _call_generate_with(gen_arg):
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

    try:
        out = _call_generate_with(gen)
    except Exception as e:
        msg = str(e)
        # Enable the safe fallback only when the error clearly indicates that generator is unsupported and fallback is allowed
        need_fallback = (
            ALLOW_GENERATOR_FALLBACK
            and do_sample
            and seed_to_use is not None
            # Stricter check: both core phrases must be present
            and ("not used by the model" in msg)
            and ("generator" in msg)
        )
        if not need_fallback:
            raise
        print("[server] generator not accepted by model; falling back to global RNG seeding")
        # Fallback path: guard the global RNG with a mutex to avoid interference across parallel threads
        with _GLOBAL_RNG_LOCK:
            try:
                torch.manual_seed(seed_to_use)
                if torch.cuda.is_available():
                    torch.cuda.manual_seed_all(seed_to_use)
            except Exception:
                pass
            out = _call_generate_with(None)
    
    seqs = out.sequences  # [1, L+new]
    eos = model.generation_config.eos_token_id
    eos_ids = [eos] if isinstance(eos, int) else [int(x) for x in (eos or [])]
    new_lens, reasons = _count_new_and_reason(seqs, prompt_len, capped, eos_ids, tokenizer.pad_token_id)
    text = tokenizer.batch_decode(seqs[:, prompt_len:], skip_special_tokens=True)[0]
    comp = new_lens[0]
    total = prompt_len + comp
    return text, prompt_len, comp, total, reasons[0]

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

        # Assemble two independent clones of the internal-only chain plus one external chain, which may be empty
        lp_internal_for_internal = _resolve_lp_list(
            internal_names=req.internal_processor_names,
            external_names=None,
            mode="internal_only"
        )
        lp_internal_for_both = _resolve_lp_list(
            internal_names=req.internal_processor_names,
            external_names=None,
            mode="internal_only"
        )
        lp_external = _resolve_lp_list(
            internal_names=None,
            external_names=req.external_processor_names,
            mode="any",
            external_params=req.external_processor_params
        )

        # Build the internal-plus-external processor chain while preserving order: internal first, external second
        if lp_internal_for_both is None and lp_external is None:
            lp_both = None
        elif lp_internal_for_both is None:
            lp_both = lp_external
        elif lp_external is None:
            lp_both = lp_internal_for_both
        else:
            lp_both = LogitsProcessorList(list(lp_internal_for_both) + list(lp_external))

        # Run two independent generate calls with the same seed so that differences come only from the external processor chain
        try:
            # ====== Generation timing: first branch (without watermark logits processor) ======
            t_gen0_start = _time.perf_counter()
            text_internal, prompt_tok_0, comp_tok_0, total_tok_0, fr_internal = await asyncio.to_thread(
                _hf_generate_single,
                inputs,
                lp_internal_for_internal,
                req.temperature,
                req.top_p,
                req.max_tokens,
                req._do_sample,
                req.rng_seed,
            )
            t_gen0_end = _time.perf_counter()

            # ====== Generation timing: second branch (with watermark logits processor added) ======
            t_gen1_start = _time.perf_counter()
            text_both, prompt_tok_1, comp_tok_1, total_tok_1, fr_both = await asyncio.to_thread(
                _hf_generate_single,
                inputs,
                lp_both,
                req.temperature,
                req.top_p,
                req.max_tokens,
                req._do_sample,
                req.rng_seed,
            )
            t_gen1_end = _time.perf_counter()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"bad_sampling_args: {e}") from e
        except torch.cuda.OutOfMemoryError as e:
            try:
                torch.cuda.empty_cache()
            except Exception:
                pass
            raise HTTPException(status_code=503, detail="generation_error: cuda_oom") from e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"generation_error: {e.__class__.__name__}: {e}") from e

        # ====== Log generation timing ======
        gen_internal_s = float(t_gen0_end - t_gen0_start)
        gen_both_s = float(t_gen1_end - t_gen1_start)
        logger.info(
            "[timing] generation internal_only=%s internal_plus_external=%s",
            _fmt_ms(gen_internal_s), _fmt_ms(gen_both_s),
        )

        # ====== Offline zero-argument detection for the external chain: only run when an external chain exists and text was generated ======
        wm_detection_result: Dict[str, Any] = {}
        det_elapsed_s: Optional[float] = None
        try:
            if lp_external is not None and comp_tok_1 > 0:
                # Optional: log the accumulated time spent inside external logits processors themselves, which is a purer overhead measure
                try:
                    for idx, proc in enumerate(list(lp_external)):
                        if hasattr(proc, "timing") and callable(getattr(proc, "timing")):
                            tinfo = proc.timing()
                            total_s = float(tinfo.get("lp_total_time_s", 0.0))
                            calls = int(tinfo.get("lp_calls", 0))
                            avg_us = float(tinfo.get("lp_avg_per_call_us", 0.0))
                            logger.info(
                                "[timing] wm_lp %s[%d] lp_total=%s lp_calls=%d lp_avg=%0.3fus",
                                proc.__class__.__name__, idx, _fmt_ms(total_s), calls, avg_us
                            )
                except Exception as _e:
                    logger.info("[timing] wm_lp timing read failed: %s: %s", _e.__class__.__name__, _e)

                t_det_start = _time.perf_counter()
                # Iterate over processor instances in the external chain; if detect_last() is implemented, call it directly without arguments
                for idx, proc in enumerate(list(lp_external)):
                    if hasattr(proc, "detect_last") and callable(getattr(proc, "detect_last")):
                        key = f"{proc.__class__.__name__}[{idx}]"
                        try:
                            wm_detection_result[key] = proc.detect_last()
                        except Exception as _e:
                            wm_detection_result[key] = {"error": f"detection_failed: {_e.__class__.__name__}: {_e}"}
                t_det_end = _time.perf_counter()
                det_elapsed_s = float(t_det_end - t_det_start)
        except Exception as _outer_e:
            wm_detection_result = {"__error__": f"{_outer_e.__class__.__name__}: {_outer_e}"}

        # ====== Log detection timing for detect_last ======
        if det_elapsed_s is not None:
            logger.info("[timing] watermark_detect(detect_last)=%s", _fmt_ms(det_elapsed_s))

        if USAGE_PER_CHOICE:
            # New accounting mode: each choice carries its own usage; no top-level usage is returned in parallel mode
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
                        "variant": "internal_only",
                        "usage": {
                            "prompt_tokens": int(prompt_tok_0),
                            "completion_tokens": int(comp_tok_0),
                            "total_tokens": int(total_tok_0),
                        },
                    },
                    {
                        "index": 1,
                        "message": {"role": "assistant", "content": text_both},
                        "finish_reason": fr_both,
                        "variant": "internal_plus_external",
                        "wm_detection": wm_detection_result,
                        "usage": {
                            "prompt_tokens": int(prompt_tok_1),
                            "completion_tokens": int(comp_tok_1),
                            "total_tokens": int(total_tok_1),
                        },
                    },
                ],
            }
        else:
            # Legacy accounting mode: merged statistics, fully preserving previous behavior
            prompt_tok = int(prompt_tok_0)
            comp_tok_sum = int(comp_tok_0 + comp_tok_1)
            total_tok = int(prompt_tok + comp_tok_sum)
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
                        "variant": "internal_plus_external",
                        "wm_detection": wm_detection_result,
                    }
                ],
                "usage": {
                    "prompt_tokens": prompt_tok,
                    "completion_tokens": comp_tok_sum,
                    "total_tokens": total_tok
                }
            }

    # Non-parallel mode: use plain generate (batch=1) and apply only your internal chain, aligned with the parallel internal-only path
    lp_internal_only = _resolve_lp_list(
        internal_names=req.internal_processor_names,
        external_names=None,
        mode="internal_only",
    )
    try:
        text, prompt_tok, comp_tok, total_tok, fr = await asyncio.to_thread(
            _hf_generate_single,
            inputs,
            lp_internal_only,
            req.temperature,
            req.top_p,
            req.max_tokens,
            req._do_sample,
            req.rng_seed,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"bad_sampling_args: {e}") from e
    except torch.cuda.OutOfMemoryError as e:
        try:
            torch.cuda.empty_cache()
        except Exception:
            pass
        raise HTTPException(status_code=503, detail="generation_error: cuda_oom") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"generation_error: {e.__class__.__name__}: {e}") from e
    # fr is already produced inside _hf_generate_single
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
