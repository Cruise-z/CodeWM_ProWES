#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
count_tokens.py
- Count how many tokens a local vLLM model uses for a given prompt
- Supports three methods:
  A) server: send a minimal `max_tokens=1` request to the local `/v1/chat/completions` endpoint and read `usage.prompt_tokens` (closest to real behavior)
  B) hf:     compute locally with an HF tokenizer plus chat template (requires `transformers`)
    Usage: `python count_tokens.py --prompt_path ./SnakeGame.java.prompt.txt --method hf --model "Qwen/Qwen2.5-Coder-32B-Instruct"`
  C) api:    call vLLM's `/tokenize` or `/v1/tokenize` endpoint (if your service version enables the Tokenizer API)
"""

import os, json, argparse, sys
from pathlib import Path

# Disable proxies and connect directly to localhost
for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
    os.environ.pop(k, None)
os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost,::1")

DEFAULT_BASE   = "http://127.0.0.1:8000"
DEFAULT_MODEL  = "Qwen/Qwen2.5-Coder-32B-Instruct"

def read_text(path: str) -> str:
    p = Path(path)
    return p.read_text(encoding="utf-8", errors="ignore")

# ---------------- A) Read usage.prompt_tokens via chat.completions ----------------
def count_via_server(messages, base_url=DEFAULT_BASE, model=DEFAULT_MODEL, timeout_s=600):
    import httpx
    from openai import OpenAI

    client = OpenAI(
        base_url=f"{base_url}/v1",
        api_key="EMPTY",
        http_client=httpx.Client(
            proxies=None, trust_env=False,
            timeout=httpx.Timeout(connect=10.0, read=timeout_s, write=timeout_s, pool=60.0),
        ),
    )
    # Only generate one token and read usage.prompt_tokens
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=1,
        temperature=0,
        stream=False,
    )
    u = resp.usage
    # Some versions expose the fields in resp.usage or resp.to_dict()["usage"]
    if u:
        return {
            "prompt_tokens": getattr(u, "prompt_tokens", None),
            "completion_tokens": getattr(u, "completion_tokens", None),
            "total_tokens": getattr(u, "total_tokens", None),
            "method": "server(chat.completions, max_tokens=1)"
        }
    # Fallback
    u2 = getattr(resp, "usage", None) or {}
    return {"prompt_tokens": u2.get("prompt_tokens"), "completion_tokens": u2.get("completion_tokens"),
            "total_tokens": u2.get("total_tokens"), "method": "server(chat.completions, max_tokens=1)"}

# ---------------- B) Compute locally with HF tokenizer + chat template ----------------
def count_via_hf(messages, model=DEFAULT_MODEL):
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model, trust_remote_code=True)
    # Apply the chat template to messages, matching the idea used by vLLM chat.completions
    # Note: if you also have a system role, put it in messages[0]
    ids = tok.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,  # Keep behavior aligned with chat.completions
        return_tensors=None,
    )
    # The call above returns a list of token IDs
    if isinstance(ids, list):
        length = len(ids)
    else:
        # Some older versions may return a tensor
        length = len(ids[0]) if hasattr(ids, "__len__") else int(ids.shape[-1])
    return {"prompt_tokens": length, "method": "hf(tokenizer.apply_chat_template + tokenize)"}

# ---------------- C) Call the vLLM Tokenizer API (if enabled) ----------------
def count_via_vllm_tokenizer(text, base_url=DEFAULT_BASE, model=DEFAULT_MODEL, timeout_s=60):
    """
    According to the vLLM docs, the Tokenizer API wraps HF and usually exposes `/tokenize` (or `/v1/tokenize`).
    The exact schema may vary by version, so this function tries:
      1) POST /v1/tokenize {"model": "...", "text": "..."}
      2) POST /v1/tokenize {"text": "..."}
      3) POST /tokenize    {"text": "..."}
    The response may contain either `{"tokens": [...]}` or `{"input_ids": [...]}`.
    """
    import httpx
    sess = httpx.Client(proxies=None, trust_env=False, timeout=timeout_s)
    payloads = [
        (f"{base_url}/v1/tokenize", {"model": model, "text": text}),
        (f"{base_url}/v1/tokenize", {"text": text}),
        (f"{base_url}/tokenize",    {"text": text}),
    ]
    last_err = None
    for url, body in payloads:
        try:
            r = sess.post(url, json=body)
            if r.status_code == 200:
                data = r.json()
                toks = data.get("tokens") or data.get("input_ids")
                if toks:
                    return {"prompt_tokens": len(toks), "method": f"vllm {url}"}
        except Exception as e:
            last_err = e
    raise RuntimeError(f"Tokenizer API not available or schema mismatched; last_err={last_err}")

def to_messages(text: str, role: str = "user", system: str = None):
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": role, "content": text})
    return msgs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt_path", type=str, required=True, help="Path to the prompt text file to count (used as a user message)")
    ap.add_argument("--method", choices=["server", "hf", "api"], default="server",
                    help="server=chat.completions usage, hf=local tokenizer, api=vLLM Tokenizer API")
    ap.add_argument("--base_url", type=str, default=DEFAULT_BASE, help="Base URL of the local vLLM service, for example http://127.0.0.1:8000")
    ap.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Served model name in vLLM")
    ap.add_argument("--system", type=str, default=None, help="Optional: add a system message")
    args = ap.parse_args()

    text = read_text(args.prompt_path)
    messages = to_messages(text, role="user", system=args.system)

    if args.method == "server":
        out = count_via_server(messages, base_url=args.base_url, model=args.model)
    elif args.method == "hf":
        out = count_via_hf(messages, model=args.model)
    else:
        out = count_via_vllm_tokenizer(text, base_url=args.base_url, model=args.model)

    print(json.dumps({
        "model": args.model,
        "base_url": args.base_url,
        "method": out["method"],
        "prompt_tokens": out["prompt_tokens"],
        "tips": "The server method best reflects vLLM's real prompt assembly and special tokens; the hf method requires a recent transformers version and a model with a chat template."
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
