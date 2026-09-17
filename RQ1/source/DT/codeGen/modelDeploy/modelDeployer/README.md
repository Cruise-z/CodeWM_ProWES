# 操作指南

## 启动模型服务

模型启动方式：

### 常规
```bash
CUDA_VISIBLE_DEVICES=0 LOG_REQ_BODY=1 LOG_REQ_BODY_BYTES=8192 SERVER_DO_SAMPLE=1 SAMPLING_MODE=lenient_openai uvicorn server:app --host 0.0.0.0 --port 8000
```



### DEBUG启动：
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

错误诊断默认开启。模型加载、regWM 注册、processor 构造、generation 失败时，部署终端会打印完整 traceback 和 CUDA/torch 环境快照。若需要关闭，可设置：

```bash
MODEL_DEPLOYER_VERBOSE_ERRORS=0 uvicorn server:app --host 0.0.0.0 --port 8000
```



### 单 worker，超时都拉长
```bash
CUDA_VISIBLE_DEVICES=0 LOG_REQ_BODY=1 LOG_REQ_BODY_BYTES=8192 SERVER_DO_SAMPLE=1 SAMPLING_MODE=lenient_openai \
gunicorn server:app \
  -k uvicorn.workers.UvicornWorker \
  -w 1 -b 0.0.0.0:8000 \
  --timeout 600 --graceful-timeout 600 --keep-alive 300 \
  --log-level debug
```



## 模型包装测试：

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
    "watermark_detect": true,
    "max_tokens": 2048
  }' | jq .
```

`watermark_detect` 默认是 `true`，会在生成结束后对外置水印处理器调用零参 `detect_last()` 并把耗时打印到部署终端。只想测生成吞吐时可传 `false`，此时仍会打印 logits processor 的累计耗时，但跳过末尾检测。

### 扩展方法

EvoSeal 仍是 `RESERVED / NOT_YET_DEFINED`，不会在基线服务启动时注册或强制导入。现有方法分别在自身包的 `codewm_integration.py` 中拥有调用顺序、参数接口、资源选择和检测能力；所有活跃方法都会先经过拓扑编译，编译结果再选择 `topology_native` 或 `topology_explicit` 执行后端。状态型检测方法还必须声明生成结束证据收口，保证最终采样 token 参与检测。F008 将 `temp/codeip` 的完整可部署 CodeIP 运行逻辑、Java PDA checkpoint 和复现代码迁入方法包，其余既有方法的数学实现保持不变。未来方法可作为 `libWM` 直接子包被自动发现，也可通过 `CODEWM_METHOD_MODULES` 加载；两种方式都必须导出完整 `CODEWM_PLUGIN`，旧 `register_external_builder()` 只保留兼容用途。无需修改 `regWM.py`。完整协议见仓库根目录 `docs/method_extension_contract.md`。

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




## 压力测试：

### 常规压测

```bash
python3 - <<'PY' | curl --noproxy 127.0.0.1,localhost -sS http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' -d @- | jq .
import json
N_CHUNKS = 12   # 先小到 50/100 验证，再逐步加到 800/2000/5000

header = (
  "你现在是一个严格的审校器。请阅读下面的超长技术文档片段集合，"
  "最后仅输出“OK:已读完毕且可解析”。不要复述内容。\n\n"
  "====== 文档开始 ======\n"
)
def chunk(i:int)->str:
    nums = ",".join(str((i*j)%997) for j in range(96))
    code = f"def f_{i}(x):\\n    return (x**2 + {i}) % 997\\n"
    kvs  = { "idx": i, "sha": f"{i:04x}{(i*i)%65535:04x}", "tags": ["llm","stress","ctx","中文","混排"], "nums_len": 96 }
    lines = [
        f"### 段落 {i:04d} —— 混合中英/符号/代码/CSV",
        "BFS vs DFS quick note: BFS explores level by level; DFS dives deep; 这句是token化噪声。",
        f"CSV::{nums}",
        "公式: S(n)=n(n+1)/2，附加冗余字符提升token密度——αβγδεζηθκλμνξοπρστυφχψω。",
        "JSON::" + json.dumps(kvs, ensure_ascii=False),
        "CODE::\\n" + code
    ]
    return "\\n".join(lines) + "\\n"

body = "".join(chunk(i) for i in range(N_CHUNKS))
tail = "====== 文档结束 ======\\n"

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



### 并行压测

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
