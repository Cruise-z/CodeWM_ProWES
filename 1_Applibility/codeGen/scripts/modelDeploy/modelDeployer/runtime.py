# runtime.py

from typing import List
import torch, os
from transformers import AutoModelForCausalLM, AutoTokenizer

# MODEL_ID = "Qwen/Qwen2.5-Coder-32B-Instruct"
MODEL_ID = "/home/zhaorz/.cache/modelscope/hub/models/Qwen/Qwen3.6-27B"
MODEL_ID = "/home/zhaorz/.cache/modelscope/hub/models/Qwen/Qwen3-Coder-30B-A3B-Instruct"

# Load tokenizer/model. Do NOT enable any built-in watermark by default.
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

def _parse_max_memory():
    """
    Optional multi-GPU memory limit.

    Example:
        export GPU_MAX_MEMORY="22GiB,22GiB,22GiB,22GiB"

    The number of values must match the number of visible CUDA devices.
    CUDA_VISIBLE_DEVICES controls which physical GPUs are visible.
    """
    raw = os.getenv("GPU_MAX_MEMORY", "").strip()
    if not raw:
        return None

    if not torch.cuda.is_available():
        return None

    parts = [x.strip() for x in raw.split(",") if x.strip()]
    visible_n = torch.cuda.device_count()

    if len(parts) != visible_n:
        raise ValueError(
            f"GPU_MAX_MEMORY expects {visible_n} comma-separated values, "
            f"got {len(parts)}: {raw}"
        )

    return {i: parts[i] for i in range(visible_n)}

max_memory = _parse_max_memory()

model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    dtype=torch.bfloat16,
    device_map="auto",
    max_memory=max_memory,
)
model.eval()

print("[runtime] CUDA_VISIBLE_DEVICES =", os.getenv("CUDA_VISIBLE_DEVICES"))
print("[runtime] cuda_device_count    =", torch.cuda.device_count())
print("[runtime] GPU_MAX_MEMORY       =", os.getenv("GPU_MAX_MEMORY"))
print("[runtime] hf_device_map        =", getattr(model, "hf_device_map", None))
print("[runtime] model first param device =", next(model.parameters()).device)
print("[runtime] model dtype              =", next(model.parameters()).dtype)
print("[runtime] model class              =", model.__class__)

# Generation-time config safety: ensure pad/eos are set to avoid warnings or invalid ids.
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
    pass

# Vocab ids for external builders. Enforce contiguous ids [0..N-1] to avoid ordering issues.
vocab_ids: List[int] = list(range(len(tokenizer)))
