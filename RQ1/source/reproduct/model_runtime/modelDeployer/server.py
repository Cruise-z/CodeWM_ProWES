# server.py
# pip install "transformers>=4.41" fastapi uvicorn pydantic torch accelerate

import os
import sys
import json
import time
import asyncio
import logging
import importlib
from typing import Any, Dict, List, Mapping, Optional

from error_report import install_excepthooks, report_exception

install_excepthooks("model-deployer-server")

try:
    import torch
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, PrivateAttr
    from starlette.middleware.base import BaseHTTPMiddleware
    from transformers import LogitsProcessorList

    from config import SERVER_DO_SAMPLE, LOG_REQ_BODY, LOG_REQ_BODY_BYTES
    from runtime import MODEL_ID, model, tokenizer, vocab_ids
    from processors import (
        INTERNAL_PROCESSORS, EXTERNAL_PROCESSORS, EXTERNAL_BUILDERS,
        EXTERNAL_METHOD_PLUGINS, EXTERNAL_PLACEMENTS,
        FrameworkRuntimeComponents, MethodIntegrationPlugin, MethodRuntimeContext,
        register_method_plugin,
        validate_processor_detection_result,
        resolve_internal, resolve_external, concat_lp,
    )
    from generation import prep_inputs, model_ctx_limit, hf_generate_single, fmt_ms
    from libWM.standalone_detection import detect_text, prepare_standalone_detector
    from libWM.timing import runtime_observation, synchronize_all_cuda_devices
except Exception as exc:
    report_exception("server import/startup failed", exc)
    raise

logger = logging.getLogger("server")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

FRAMEWORK_RUNTIME_COMPONENTS = FrameworkRuntimeComponents(
    tokenizer=tokenizer,
    model=model,
    tokenizer_vocab_ids=vocab_ids,
)

# -------------------------
# OpenAI-compatible schemas
# -------------------------
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: Optional[str] = MODEL_ID
    messages: List[Message]
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.95
    max_tokens: Optional[int] = 512
    stream: Optional[bool] = False  # This server does not implement streaming in this example.

    # Optional: request-scoped RNG seed for reproducible sampling across runs.
    rng_seed: Optional[int] = None

    # Processor names (must be registered in registries)
    internal_processor_names: Optional[List[str]] = None
    external_processor_names: Optional[List[str]] = None

    # Only applies to external builders: per-name parameter dict
    external_processor_params: Optional[Dict[str, Dict[str, Any]]] = None
    watermark_detect: Optional[bool] = True
    # v2 timing controls. Defaults preserve the RQ1 generation/detection path.
    instrument_processor_timing: Optional[bool] = True
    capture_detection_state: Optional[bool] = True
    force_max_tokens: Optional[bool] = False

    # Hidden knob (not in schema): server default sampling policy
    _do_sample: bool = PrivateAttr(default=SERVER_DO_SAMPLE)

# Standalone extraction request schema.
class WatermarkDetectionRequest(BaseModel):
    method: str
    text: str
    method_params: Optional[Dict[str, Any]] = None
    rng_seed: Optional[int] = 1234
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0


# FastAPI app
# -------------------------
app = FastAPI()

@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception):
    report_exception(f"unhandled request error: {request.method} {request.url.path}", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": f"internal_server_error: {exc.__class__.__name__}: {exc}"},
    )

class LogReqSizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Paths to log
        if request.url.path in ("/v1/chat/completions", "/v1/watermark/detect", "/dbg/echo-len"):
            try:
                body = await request.body()
                size = len(body or b"")
                cl = request.headers.get("content-length")
                logger.info("[recv] bytes=%s content-length=%s path=%s", size, cl, request.url.path)

                if LOG_REQ_BODY:
                    preview = body[:LOG_REQ_BODY_BYTES]
                    printed = None
                    try:
                        parsed = json.loads(preview.decode("utf-8", "replace"))
                        printed = json.dumps(parsed, ensure_ascii=False, indent=2)
                    except Exception:
                        printed = preview.decode("utf-8", "replace")
                    logger.info("[recv] body_preview(%d/%dB): %s", len(preview), size, printed)
            except Exception as e:
                logger.warning("[recv] failed to read body: %r", e)

        return await call_next(request)

app.add_middleware(LogReqSizeMiddleware)

@app.get("/v1/_processors")
def list_processors():
    """Debug endpoint: list currently registered processor names."""
    return {
        "internal": list(INTERNAL_PROCESSORS.keys()),
        "external": list(EXTERNAL_PROCESSORS.keys()),  # legacy compat
        "external_builders": list(EXTERNAL_BUILDERS.keys()),
        "method_plugins": list(EXTERNAL_METHOD_PLUGINS.keys()),
        "method_framework_components": {
            name: [
                component.value
                for component in plugin.required_framework_components
            ]
            for name, plugin in EXTERNAL_METHOD_PLUGINS.items()
        },
        "method_contracts": {
            name: {
                "parameters": plugin.parameter_contract.as_dict(),
                "detection": plugin.detection_contract.as_dict(),
                **plugin.contract.as_dict(),
                "variants": [
                    contract.as_dict()
                    for contract in plugin.contracts
                ],
                "final_generation_evidence": (
                    plugin.generation_evidence_finalizer is not None
                ),
            }
            for name, plugin in EXTERNAL_METHOD_PLUGINS.items()
        },
        "external_placements": {
            name: (
                spec.placement.value
                if spec.placement is not None
                else "processor_declared"
            )
            for name, spec in EXTERNAL_PLACEMENTS.items()
        },
        "external_component_orders": {
            name: [
                None if order is None else order.as_dict()
                for order in spec.component_orders
            ]
            for name, spec in EXTERNAL_PLACEMENTS.items()
            if spec.component_orders
        },
    }

@app.get("/v1/models")
def list_models():
    """OpenAI-compatible: list a single model."""
    return {"object": "list", "data": [{"id": MODEL_ID, "object": "model"}]}

@app.get("/healthz")
def healthz():
    """Simple health check."""
    return {"status": "ok", "model": MODEL_ID}

@app.post("/dbg/echo-len")
async def dbg_echo_len(request: Request):
    """Debug endpoint: return request body length."""
    try:
        body = await request.body()
        cl = request.headers.get("content-length")
        return {"len": len(body or b""), "content_length": cl}
    except Exception as e:
        logger.warning("[dbg/echo-len] failed to read body: %r", e)
        raise HTTPException(status_code=500, detail=f"echo_len_error: {e}")

def _load_regwm():
    """Load and validate the mandatory in-tree method plugin registry."""
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:
            sys.path.insert(0, here)
        importlib.import_module("regWM")
        print("[server] processors loaded ->",
              "internal:", list(INTERNAL_PROCESSORS.keys()),
              "external_builders:", list(EXTERNAL_BUILDERS.keys()))
    except Exception as e:
        report_exception("regWM processor registration failed", e)
        raise RuntimeError("failed to load the CodeWM method plugin registry") from e


def _load_method_extensions() -> None:
    """Load opt-in complete plugins without editing the in-tree registry."""
    configured = os.getenv("CODEWM_METHOD_MODULES", "")
    module_names = [name.strip() for name in configured.split(",") if name.strip()]
    for module_name in module_names:
        try:
            module = importlib.import_module(module_name)
            plugin = getattr(module, "CODEWM_PLUGIN", None)
            if not isinstance(plugin, MethodIntegrationPlugin):
                raise TypeError(
                    f"{module_name} must export CODEWM_PLUGIN as MethodIntegrationPlugin"
                )
            registered = EXTERNAL_METHOD_PLUGINS.get(plugin.contract.name)
            if registered is None:
                register_method_plugin(plugin)
            elif registered is not plugin:
                raise ValueError(
                    f"method extension {module_name!r} conflicts with registered "
                    f"plugin {plugin.contract.name!r}"
                )
        except Exception as exc:
            report_exception(f"method extension import failed: {module_name}", exc)
            raise RuntimeError(
                f"failed to load CODEWM_METHOD_MODULES entry {module_name!r}"
            ) from exc
        print(f"[server] method extension loaded -> {module_name}")


# Load and validate method plugins once at import time.
_load_regwm()
_load_method_extensions()


def _method_runtime_context(req: ChatRequest, inputs: Dict[str, torch.Tensor]) -> MethodRuntimeContext:
    prompt_rows = tuple(
        tuple(int(token) for token in row)
        for row in inputs["input_ids"].detach().cpu().tolist()
    )
    tokenizer_vocab_size = int(getattr(tokenizer, "vocab_size", 0) or 0)
    tokenizer_length = int(len(tokenizer))
    model_vocab_size = int(getattr(model.config, "vocab_size", 0) or 0)
    output_embeddings = getattr(model, "get_output_embeddings", lambda: None)()
    output_weight = getattr(output_embeddings, "weight", None)
    output_weight_rows = (
        int(output_weight.shape[0])
        if output_weight is not None and getattr(output_weight, "ndim", 0) >= 1
        else 0
    )
    score_vocab_size = int(
        getattr(output_embeddings, "num_embeddings", 0)
        or getattr(output_embeddings, "out_features", 0)
        or output_weight_rows
        or model_vocab_size
    )
    eos = getattr(model.generation_config, "eos_token_id", None)
    eos_token_ids = (int(eos),) if isinstance(eos, int) else tuple(
        int(token) for token in (eos or ())
    )
    return MethodRuntimeContext(
        rng_seed=req.rng_seed,
        do_sample=bool(req._do_sample),
        temperature=float(req.temperature if req.temperature is not None else 1.0),
        top_p=float(req.top_p if req.top_p is not None else 1.0),
        prompt_input_ids=prompt_rows,
        tokenizer_vocab_size=tokenizer_vocab_size,
        tokenizer_length=tokenizer_length,
        model_vocab_size=model_vocab_size,
        score_vocab_size=score_vocab_size,
        eos_token_ids=eos_token_ids,
        pad_token_id=tokenizer.pad_token_id,
    )


def _format_processor_timing_details(timing: Mapping[str, Any]) -> List[str]:
    """Format method-owned timing metadata without knowing method-specific keys."""
    ignored = {"lp_total_time_s", "lp_calls", "lp_avg_per_call_us"}
    details: List[str] = []

    def append_value(name: str, value: Any) -> None:
        if isinstance(value, bool):
            details.append(f"{name}={value}")
        elif isinstance(value, int):
            details.append(f"{name}={value}")
        elif isinstance(value, float):
            rendered = fmt_ms(value) if name.endswith("_time_s") else f"{value:.6g}"
            details.append(f"{name}={rendered}")
        elif isinstance(value, str) or value is None:
            details.append(f"{name}={value}")

    for name in sorted(key for key in timing if key not in ignored):
        value = timing[name]
        if isinstance(value, Mapping):
            for nested_name in sorted(value):
                append_value(f"{name}.{nested_name}", value[nested_name])
        else:
            append_value(name, value)
    return details

@app.post("/v1/chat/completions")
async def chat(req: ChatRequest) -> Dict[str, Any]:
    # Basic validation
    if not req.messages:
        raise HTTPException(status_code=422, detail="messages must not be empty")

    if bool(req.watermark_detect) and not bool(req.capture_detection_state):
        raise HTTPException(
            status_code=422,
            detail="watermark_detect requires capture_detection_state=true",
        )

    try:
        msgs = [m.model_dump() for m in req.messages]
        inputs = prep_inputs(msgs)
    except Exception as e:
        report_exception("request prompt preparation failed", e)
        raise HTTPException(status_code=500, detail=f"prompt_preparation_error: {e.__class__.__name__}: {e}") from e

    # Prompt length guard
    try:
        prompt_len = int(inputs["input_ids"].shape[1])
    except Exception:
        prompt_len = 0

    ctx_lim = model_ctx_limit()
    if ctx_lim is not None and prompt_len > ctx_lim:
        raise HTTPException(status_code=400, detail=f"prompt_too_long: {prompt_len}>{ctx_lim}")

    lp_external = None

    # Build processors:
    # - internal processors (cloned per request)
    # - external processors via builders (cloned per request)
    try:
        lp_internal = resolve_internal(req.internal_processor_names)
        lp_external = resolve_external(
            req.external_processor_names,
            external_params=req.external_processor_params,
            runtime_context=_method_runtime_context(req, inputs),
            framework_components=FRAMEWORK_RUNTIME_COMPONENTS,
        )
        lp_final = concat_lp(lp_internal, lp_external)
    except HTTPException as e:
        if e.__cause__ is not None:
            report_exception("request processor construction failed", e.__cause__)
        raise
    except Exception as e:
        report_exception("request processor construction failed", e)
        raise HTTPException(status_code=500, detail=f"processor_error: {e.__class__.__name__}: {e}") from e

    # Run a single generate() call (no more "parallel" dual-path).
    try:
        with runtime_observation(
            processor_timing=bool(req.instrument_processor_timing),
            detection_state=bool(req.capture_detection_state),
        ):
            text, prompt_tok, comp_tok, total_tok, finish_reason, gen_elapsed_s = await asyncio.to_thread(
                hf_generate_single,
                inputs,
                lp_final,
                req.temperature,
                req.top_p,
                req.max_tokens,
                req._do_sample,
                req.rng_seed,
                bool(req.force_max_tokens),
            )
    except ValueError as e:
        report_exception("generation value error", e)
        raise HTTPException(status_code=400, detail=f"bad_sampling_args: {e}") from e
    except torch.cuda.OutOfMemoryError as e:
        report_exception("generation CUDA out-of-memory", e)
        try:
            torch.cuda.empty_cache()
        except Exception:
            pass
        raise HTTPException(status_code=503, detail="generation_error: cuda_oom") from e
    except Exception as e:
        report_exception("generation error", e)
        logger.warning("[generation error]: %s: %s", e.__class__.__name__, e)
        raise HTTPException(status_code=500, detail=f"generation_error: {e.__class__.__name__}: {e}") from e

    logger.info("[timing] generation=%s", fmt_ms(gen_elapsed_s))

    # Optional watermark detection (only for external processors that implement detect_last()).
    wm_detection_result: Dict[str, Any] = {}
    processor_metrics: Dict[str, Dict[str, Any]] = {}
    det_elapsed_s: Optional[float] = None

    if lp_external is not None and comp_tok > 0:
        try:
            # Optional: read per-processor accumulated timing if available
            try:
                for idx, proc in enumerate(list(lp_external)):
                    if hasattr(proc, "timing") and callable(getattr(proc, "timing")):
                        tinfo = proc.timing()
                        processor_metrics[f"{proc.__class__.__name__}[{idx}]"] = dict(tinfo)
                        total_s = float(tinfo.get("lp_total_time_s", 0.0))
                        calls = int(tinfo.get("lp_calls", 0))
                        avg_us = float(tinfo.get("lp_avg_per_call_us", 0.0))
                        detail_parts = _format_processor_timing_details(tinfo)
                        logger.info(
                            "[timing] wm_lp %s[%d] lp_total=%s lp_calls=%d lp_avg=%0.3fus%s",
                            proc.__class__.__name__, idx, fmt_ms(total_s), calls, avg_us,
                            (" " + " ".join(detail_parts)) if detail_parts else "",
                        )
            except Exception as _e:
                logger.info("[timing] wm_lp timing read failed: %s: %s", _e.__class__.__name__, _e)

            if bool(req.watermark_detect):
                if torch.cuda.is_available():
                    torch.cuda.synchronize()
                t_det_start = time.perf_counter()
                for idx, proc in enumerate(list(lp_external)):
                    if hasattr(proc, "detect_last") and callable(getattr(proc, "detect_last")):
                        key = f"{proc.__class__.__name__}[{idx}]"
                        try:
                            result = proc.detect_last()
                            validate_processor_detection_result(proc, result)
                            wm_detection_result[key] = result
                        except Exception as _e:
                            wm_detection_result[key] = {"error": f"detection_failed: {_e.__class__.__name__}: {_e}"}
                if torch.cuda.is_available():
                    torch.cuda.synchronize()
                t_det_end = time.perf_counter()
                det_elapsed_s = float(t_det_end - t_det_start)
            else:
                logger.info("[timing] watermark_detect(detect_last)=skipped")
        except Exception as _outer_e:
            wm_detection_result = {"__error__": f"{_outer_e.__class__.__name__}: {_outer_e}"}

    if det_elapsed_s is not None:
        logger.info("[timing] watermark_detect(detect_last)=%s", fmt_ms(det_elapsed_s))

    # OpenAI-compatible response
    choice0: Dict[str, Any] = {
        "index": 0,
        "message": {"role": "assistant", "content": text},
        "finish_reason": finish_reason,
        "generation_metrics": {
            "generation_elapsed_s": float(gen_elapsed_s),
            "watermark_detection_elapsed_s": det_elapsed_s,
            "processor_timing_enabled": bool(req.instrument_processor_timing),
            "detection_state_enabled": bool(req.capture_detection_state),
            "force_max_tokens": bool(req.force_max_tokens),
        },
        "processor_metrics": processor_metrics,
    }

    # Attach detection results only when external processors were used
    if lp_external is not None and wm_detection_result:
        choice0["wm_detection"] = wm_detection_result

    resp: Dict[str, Any] = {
        "id": f"chatcmpl-{int(time.time()*1000)}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model,
        "choices": [choice0],
        "usage": {
            "prompt_tokens": int(prompt_tok),
            "completion_tokens": int(comp_tok),
            "total_tokens": int(total_tok),
        },
    }

    return resp


def _measure_standalone_detection(processor: Any, text: str) -> tuple[Dict[str, Any], int, float]:
    """Measure final-text tokenization plus method-owned extraction."""

    synchronize_all_cuda_devices()
    started = time.perf_counter()
    result, input_tokens = detect_text(processor, tokenizer, text)
    synchronize_all_cuda_devices()
    elapsed_s = float(time.perf_counter() - started)
    return result, input_tokens, elapsed_s


@app.post("/v1/watermark/detect")
async def detect_watermark(req: WatermarkDetectionRequest) -> Dict[str, Any]:
    """Run extraction independently from generation for the v2 timing protocol.

    Processor construction and method-specific lazy initialization are outside
    the timed boundary. Final-text tokenization, transfers performed by the
    detector, and the complete detector call are inside it.
    """

    method = req.method.strip().lower()
    if not method:
        raise HTTPException(status_code=422, detail="method must not be empty")
    if not req.text:
        raise HTTPException(status_code=422, detail="text must not be empty")

    context_req = ChatRequest(
        messages=[Message(role="user", content=req.text)],
        temperature=req.temperature,
        top_p=req.top_p,
        max_tokens=1,
        rng_seed=req.rng_seed,
        watermark_detect=False,
        instrument_processor_timing=False,
        capture_detection_state=False,
    )
    try:
        context_inputs = prep_inputs(
            [message.model_dump() for message in context_req.messages]
        )
        processors = resolve_external(
            [method],
            external_params={method: dict(req.method_params or {})},
            runtime_context=_method_runtime_context(context_req, context_inputs),
            framework_components=FRAMEWORK_RUNTIME_COMPONENTS,
        )
        if processors is None or len(processors) != 1:
            raise RuntimeError("standalone detection requires exactly one processor")
        processor = list(processors)[0]
        prepare_standalone_detector(processor)
        result, input_tokens, elapsed_s = await asyncio.to_thread(
            _measure_standalone_detection,
            processor,
            req.text,
        )
        validate_processor_detection_result(processor, result)
    except HTTPException:
        raise
    except Exception as exc:
        report_exception("standalone watermark detection failed", exc)
        raise HTTPException(
            status_code=500,
            detail=f"standalone_detection_error: {exc.__class__.__name__}: {exc}",
        ) from exc

    return {
        "method": method,
        "input_tokens": int(input_tokens),
        "extraction_elapsed_s": float(elapsed_s),
        "wm_detection": result,
        "measurement_contract": {
            "processor_construction_timed": False,
            "lazy_detector_initialization_timed": False,
            "final_text_tokenization_timed": True,
            "detector_execution_timed": True,
            "generation_state_reused": False,
            "cuda_boundary_synchronization": "all_visible_devices",
        },
    }


# Startup examples:
#   Sampling enabled:
#     uvicorn server:app --host 0.0.0.0 --port 8000
#   Sampling disabled (greedy):
#     SERVER_DO_SAMPLE=0 uvicorn server:app --host 0.0.0.0 --port 8000
#
# Optional env vars:
#   SAMPLING_MODE=lenient_openai | map_to_greedy | strict
#   LOG_REQ_BODY=1
#   LOG_REQ_BODY_BYTES=4096
#   RNG_SEED_FALLBACK=none | derived
#   DETERMINISTIC=1
