# test_parallel.py
import os
from openai import OpenAI

# 1) Point to your local service (OpenAI compatible)
BASE_URL = os.getenv("OPENAI_API_BASE", "http://127.0.0.1:8000/v1")
API_KEY  = os.getenv("OPENAI_API_KEY", "sk-local-anything")  # Use any non-empty value
MODEL    = os.getenv("OPENAI_MODEL_NAME", "Qwen/Qwen2.5-Coder-32B-Instruct")

# It is strongly recommended to bypass the proxy (otherwise you may get 502 errors)
os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost,::1")
os.environ.setdefault("no_proxy", "127.0.0.1,localhost,::1")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

def call(messages, max_tokens=256, **extra):
    """Put custom parameters such as parallel / internal_processor_names / external_processor_names into extra."""
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=max_tokens,
        # Key point: put custom fields into extra_body
        extra_body=extra,
    )
    return resp

def show(resp):
    print(f"choices = {len(resp.choices)}")
    for ch in resp.choices:
        variant = getattr(ch, "variant", None)  # Your service will include variant during parallel execution
        print("="*60)
        if variant: print(f"[variant] {variant}")
        print(ch.message.content)

if __name__ == "__main__":
    msgs = [{"role":"user","content":"Explain the differences between BFS and DFS and give examples. Keep it brief."}]

    print("\n[Case 1] Non-parallel, no processors (baseline)")
    r1 = call(msgs)
    show(r1)

    print("\n[Case 2] Parallel: path 0 = built-in only, path 1 = built-in + external")
    # Replace with the processor names you actually registered; you can pass multiple external ones
    r2 = call(
        msgs,
        parallel=True,
        internal_processor_names=[],
        external_processor_names=["wllm", "sweet"],
        max_tokens=256,
    )
    show(r2)

    print("\n[Case 3] Parallel: built-in only (external empty) — used to compare the two paths under sampling/greedy")
    # Note: if your server globally sets SERVER_DO_SAMPLE=0 (greedy), the two paths should naturally match;
    # if sampling is enabled, the two paths may diverge because each samples independently.
    r3 = call(
        msgs,
        parallel=True,
        internal_processor_names=[],
        external_processor_names=[],
        max_tokens=256,
    )
    show(r3)
