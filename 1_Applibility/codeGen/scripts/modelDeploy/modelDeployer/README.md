# User Guide

## Start the model service

Model startup commands:

### Standard
```bash
CUDA_VISIBLE_DEVICES=0 LOG_REQ_BODY=1 LOG_REQ_BODY_BYTES=8192 SERVER_DO_SAMPLE=1 SAMPLING_MODE=lenient_openai uvicorn server:app --host 0.0.0.0 --port 8000
```



### Debug startup:
```bash
CUDA_VISIBLE_DEVICES=0 LOG_REQ_BODY=1 LOG_REQ_BODY_BYTES=8192 SERVER_DO_SAMPLE=1 SAMPLING_MODE=lenient_openai \
uvicorn server:app \
  --host 0.0.0.0 --port 8000 \
  --http httptools \
  --loop uvloop \
  --log-level debug \
  --access-log \
  --timeout-keep-alive 300
```



### Single worker with extended timeouts
```bash
CUDA_VISIBLE_DEVICES=0 LOG_REQ_BODY=1 LOG_REQ_BODY_BYTES=8192 SERVER_DO_SAMPLE=1 SAMPLING_MODE=lenient_openai \
gunicorn server:app \
  -k uvicorn.workers.UvicornWorker \
  -w 1 -b 0.0.0.0:8000 \
  --timeout 600 --graceful-timeout 600 --keep-alive 300 \
  --log-level debug
```



## Model wrapper test:

```bash
curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/v1/_processors
```

```bash
curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model":"Qwen/Qwen2.5-Coder-32B-Instruct",
    "messages":[{"role":"user","content":"讲讲BFS与DFS差异并举例"}],
    "parallel": true,
    "temperature":0.7,
    "rng_seed": 123456,
    "internal_processor_names":[],
    "external_processor_names":["sweet"],
    "external_processor_params": {
      "sweet": {"gamma":0.7,"delta":0.08,"entropy_threshold":0.85},
      "wllm":  {"gamma":0.4,"delta":1}
    },
    "max_tokens": 2048
  }' | jq .
```

```bash
curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model":"Qwen/Qwen2.5-Coder-32B-Instruct",
    "messages":[{"role":"user","content":"讲讲BFS与DFS差异并举例"}],
    "temperature": 0.7,
    "rng_seed": 123456,
    "max_tokens": 2048
  }' | jq .
```




## Stress test:

### Standard stress test

```bash
python3 - <<'PY' | curl --noproxy 127.0.0.1,localhost -sS http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' -d @- | jq .
import json
N_CHUNKS = 12   # Start small with 50/100 for validation, then gradually increase to 800/2000/5000

header = (
  "You are now a strict proofreader. Please read the following collection of long technical document fragments,"
  "and finally output only \"OK: read and parse complete.\" Do not repeat the content.\n\n"
  "====== Document begins ======\n"
)
def chunk(i:int)->str:
    nums = ",".join(str((i*j)%997) for j in range(96))
    code = f"def f_{i}(x):\\n    return (x**2 + {i}) % 997\\n"
    kvs  = { "idx": i, "sha": f"{i:04x}{(i*i)%65535:04x}", "tags": ["llm","stress","ctx","Chinese","mixed"], "nums_len": 96 }
    lines = [
        f"### Paragraph {i:04d} —— mixed Chinese/English/symbols/code/CSV",
        "BFS vs DFS quick note: BFS explores level by level; DFS dives deep; this sentence is tokenization noise.",
        f"CSV::{nums}",
        "Formula: S(n)=n(n+1)/2, with extra redundant characters to increase token density — αβγδεζηθκλμνξοπρστυφχψω.",
        "JSON::" + json.dumps(kvs, ensure_ascii=False),
        "CODE::\\n" + code
    ]
    return "\\n".join(lines) + "\\n"

body = "".join(chunk(i) for i in range(N_CHUNKS))
tail = "====== Document ends ======\n"

payload = {
  "model":"Qwen/Qwen2.5-Coder-32B-Instruct",
  "messages":[{"role":"user","content": header + body + tail}],
  "temperature":0.0,
  "top_p":1.0,
  "max_tokens":16,
  "stream": False
}
print(json.dumps(payload, ensure_ascii=False))
PY
```



### Parallel stress test

```bash
python3 - <<'PY' | curl --max-time 120 --noproxy 127.0.0.1,localhost -sS http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' -d @- | jq .
import json
N_CHUNKS = 260
header = "并行压测：请读完整个大段文本后仅回复“OK:parallel:zrz zzzzz”。\\n\\n"
def chunk(i): return f"[{i:04d}] 压测行 {i} —— tokens*mix —— 0123456789 ABC abc XYZ。\\n"
body = "".join(chunk(i) for i in range(N_CHUNKS))
payload = {
  "model":"Qwen/Qwen2.5-Coder-32B-Instruct",
  "messages":[{"role":"user","content": header + body}],
  "temperature":0.0, "top_p":1.0,
  "max_tokens":16, "stream": False,
  "internal_processor_names": [],
  "external_processor_names": ["sweet"],
  "parallel": True
}
print(json.dumps(payload, ensure_ascii=False))
PY
```