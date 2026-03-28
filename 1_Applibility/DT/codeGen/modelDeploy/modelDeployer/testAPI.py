# test_parallel.py
import os
from openai import OpenAI

# 1) Point to your local service (OpenAI-compatible)
BASE_URL = os.getenv("OPENAI_API_BASE", "http://127.0.0.1:8000/v1")
API_KEY  = os.getenv("OPENAI_API_KEY", "sk-local-anything")  # Any non-empty value is fine
MODEL    = os.getenv("OPENAI_MODEL_NAME", "Qwen/Qwen2.5-Coder-32B-Instruct")

# Strongly recommended: bypass proxies, otherwise you may get 502 errors
os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost,::1")
os.environ.setdefault("no_proxy", "127.0.0.1,localhost,::1")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

def call(messages, max_tokens=256, **extra):
    """Put custom parameters such as parallel / internal_processor_names / external_processor_names into extra."""
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=max_tokens,
        # Key point: place custom fields into extra_body
        extra_body=extra,
    )
    return resp

def show(resp):
    print(f"choices = {len(resp.choices)}")
    for ch in resp.choices:
        variant = getattr(ch, "variant", None)  # Your service includes variant in parallel mode
        print("="*60)
        if variant: print(f"[variant] {variant}")
        print(ch.message.content)

if __name__ == "__main__":
    msgs = [{"role":"user","content":"Explain the differences between BFS and DFS and give short examples."}]

    print("\n[Case 1] Non-parallel, no processors (baseline)")
    r1 = call(msgs)
    show(r1)

    print("\n[Case 2] Parallel: branch 0 = internal only, branch 1 = internal + external")
    # Replace these with the processor names actually registered in your environment; multiple external processors are allowed
    r2 = call(
        msgs,
        parallel=True,
        internal_processor_names=[],
        external_processor_names=["wllm", "sweet"],
        max_tokens=256,
    )
    show(r2)

    print("\n[Case 3] Parallel: internal only (external empty) -- used to observe how the two branches behave under sampling/greedy decoding")
    # Note: if the server-side global SERVER_DO_SAMPLE=0 (greedy), the two branches should naturally match;
    # if sampling is enabled, they may diverge because each branch samples independently
    r3 = call(
        msgs,
        parallel=True,
        internal_processor_names=[],
        external_processor_names=[],
        max_tokens=256,
    )
    show(r3)
