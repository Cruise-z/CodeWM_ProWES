# Model deployer

This directory exposes the Qwen generation runtime through an
OpenAI-compatible FastAPI endpoint and loads the in-tree watermark plugins.

## Start the server

```bash
CUDA_VISIBLE_DEVICES=0,1,2,3 \
SERVER_DO_SAMPLE=1 \
SAMPLING_MODE=lenient_openai \
python -m uvicorn server:app --host 127.0.0.1 --port 8000
```

Use `LOG_REQ_BODY=1` only for debugging because request bodies may be large.
Runtime exceptions include the Python traceback and CUDA/PyTorch environment
snapshot by default; set `CODEWM_DIAGNOSTICS=0` to disable that report.

## Inspect the runtime

```bash
curl http://127.0.0.1:8000/healthz
curl http://127.0.0.1:8000/v1/_processors
```

The processor catalog reports parameter, resource, decode-order, and detector
contracts for every discovered method plugin.

## Generate with a method

```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "messages": [{"role": "user", "content": "Implement a Java queue."}],
    "temperature": 0.7,
    "top_p": 1.0,
    "max_tokens": 256,
    "rng_seed": 42,
    "external_processor_names": ["wllm"],
    "external_processor_params": {
      "wllm": {"gamma": 0.5, "delta": 2.0}
    },
    "watermark_detect": true
  }'
```

`watermark_detect=true` invokes each external processor's zero-argument
`detect_last()` method after generation. The response includes synchronized
generation, processor, and detector timing fields used by the RQ3 harness.

## Extension contract

Each active method owns a `codewm_integration.py` plugin declaring its decode
order, accepted parameters, required framework resources, and detector score
contract. Plugins in direct `libWM` child packages are discovered
automatically. Optional external modules can be listed in
`CODEWM_METHOD_MODULES`; each must export a complete `CODEWM_PLUGIN`.

The legacy EvoSeal hook remains reserved and is not loaded by the baseline
server. See the artifact-level method configuration and source provenance for
the set of evaluated plugins.
