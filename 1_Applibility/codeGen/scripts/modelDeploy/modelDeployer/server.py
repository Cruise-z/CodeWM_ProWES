# server.py
# pip install "transformers>=4.41" fastapi uvicorn pydantic torch accelerate

import os
import sys
import json
import time
import asyncio
import logging
import importlib
from typing import Any, Dict, List, Optional

import torch
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, PrivateAttr
from starlette.middleware.base import BaseHTTPMiddleware
from transformers import LogitsProcessorList

from config import SERVER_DO_SAMPLE, LOG_REQ_BODY, LOG_REQ_BODY_BYTES
from runtime import MODEL_ID
from processors import (
    INTERNAL_PROCESSORS, EXTERNAL_PROCESSORS, EXTERNAL_BUILDERS,
    resolve_internal, resolve_external, concat_lp,
)
from generation import prep_inputs, model_ctx_limit, hf_generate_single, fmt_ms

logger = logging.getLogger("server")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

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

    # Hidden knob (not in schema): server default sampling policy
    _do_sample: bool = PrivateAttr(default=SERVER_DO_SAMPLE)

# -------------------------
# FastAPI app
# -------------------------
app = FastAPI()

class LogReqSizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Paths to log
        if request.url.path in ("/v1/chat/completions", "/dbg/echo-len"):
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

def _maybe_load_regwm():
    """
    Optional plugin loader: tries to import regWM (which should register processors/builders at import time).
    """
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:
            sys.path.insert(0, here)
        importlib.import_module("regWM")
        print("[server] processors loaded ->",
              "internal:", list(INTERNAL_PROCESSORS.keys()),
              "external_builders:", list(EXTERNAL_BUILDERS.keys()))
    except Exception as e:
        print(f"[server] regWM not loaded: {e}")

# Load regWM once at import time (optional)
_maybe_load_regwm()

@app.post("/v1/chat/completions")
async def chat(req: ChatRequest) -> Dict[str, Any]:
    # Basic validation
    if not req.messages:
        raise HTTPException(status_code=422, detail="messages must not be empty")

    msgs = [m.model_dump() for m in req.messages]
    inputs = prep_inputs(msgs)

    # Prompt length guard
    try:
        prompt_len = int(inputs["input_ids"].shape[1])
    except Exception:
        prompt_len = 0

    ctx_lim = model_ctx_limit()
    if ctx_lim is not None and prompt_len > ctx_lim:
        raise HTTPException(status_code=400, detail=f"prompt_too_long: {prompt_len}>{ctx_lim}")

    # Build processors:
    # - internal processors (cloned per request)
    # - external processors via builders (cloned per request)
    lp_internal = resolve_internal(req.internal_processor_names)
    lp_external = resolve_external(req.external_processor_names, external_params=req.external_processor_params)
    lp_final = concat_lp(lp_internal, lp_external)

    # Run a single generate() call (no more "parallel" dual-path).
    try:
        text, prompt_tok, comp_tok, total_tok, finish_reason, gen_elapsed_s = await asyncio.to_thread(
            hf_generate_single,
            inputs,
            lp_final,
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
        logger.warning("[generation error]: %s: %s", e.__class__.__name__, e)
        raise HTTPException(status_code=500, detail=f"generation_error: {e.__class__.__name__}: {e}") from e

    logger.info("[timing] generation=%s", fmt_ms(gen_elapsed_s))

    # Optional watermark detection (only for external processors that implement detect_last()).
    wm_detection_result: Dict[str, Any] = {}
    det_elapsed_s: Optional[float] = None

    if lp_external is not None and comp_tok > 0:
        try:
            # Optional: read per-processor accumulated timing if available
            try:
                for idx, proc in enumerate(list(lp_external)):
                    if hasattr(proc, "timing") and callable(getattr(proc, "timing")):
                        tinfo = proc.timing()
                        total_s = float(tinfo.get("lp_total_time_s", 0.0))
                        calls = int(tinfo.get("lp_calls", 0))
                        avg_us = float(tinfo.get("lp_avg_per_call_us", 0.0))
                        logger.info(
                            "[timing] wm_lp %s[%d] lp_total=%s lp_calls=%d lp_avg=%0.3fus",
                            proc.__class__.__name__, idx, fmt_ms(total_s), calls, avg_us
                        )
            except Exception as _e:
                logger.info("[timing] wm_lp timing read failed: %s: %s", _e.__class__.__name__, _e)

            t_det_start = time.perf_counter()
            for idx, proc in enumerate(list(lp_external)):
                if hasattr(proc, "detect_last") and callable(getattr(proc, "detect_last")):
                    key = f"{proc.__class__.__name__}[{idx}]"
                    # try:
                    #     wm_detection_result[key] = proc.detect_last()
                    # except Exception as _e:
                    #     wm_detection_result[key] = {"error": f"detection_failed: {_e.__class__.__name__}: {_e}"}
            t_det_end = time.perf_counter()
            det_elapsed_s = float(t_det_end - t_det_start)
        except Exception as _outer_e:
            wm_detection_result = {"__error__": f"{_outer_e.__class__.__name__}: {_outer_e}"}

    if det_elapsed_s is not None:
        logger.info("[timing] watermark_detect(detect_last)=%s", fmt_ms(det_elapsed_s))

    # OpenAI-compatible response
    choice0: Dict[str, Any] = {
        "index": 0,
        "message": {"role": "assistant", "content": text},
        "finish_reason": finish_reason,
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
