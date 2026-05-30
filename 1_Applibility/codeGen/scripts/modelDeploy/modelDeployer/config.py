# config.py
# pip install "transformers>=4.41" fastapi uvicorn pydantic torch accelerate

import os
import torch

# -------------------------
# Environment helpers
# -------------------------
def as_bool(x: str) -> bool:
    """Parse environment variable into bool."""
    return str(x).strip().lower() not in ("0", "false", "no", "off", "")

def as_mode(x: str) -> str:
    """Normalize string into {'lenient_openai','map_to_greedy','strict'}."""
    s = str(x or "").strip().lower().replace("-", "_")
    if s in ("lenient_openai", "lenient", "openai", "lo"):
        return "lenient_openai"
    if s in ("map_to_greedy", "map2greedy", "to_greedy", "greedy_map", "mg"):
        return "map_to_greedy"
    if s in ("strict", "error", "raise", "s"):
        return "strict"
    return "lenient_openai"

# -------------------------
# Sampling / RNG controls
# -------------------------
# SERVER_DO_SAMPLE: "1"/"true" enables sampling; "0"/"false" forces greedy. Default: enabled.
SERVER_DO_SAMPLE = as_bool(os.getenv("SERVER_DO_SAMPLE", "1"))

# SAMPLING_MODE: "lenient_openai" | "map_to_greedy" | "strict"
SAMPLING_MODE = as_mode(os.getenv("SAMPLING_MODE", "lenient_openai"))

# Enable fallback when a model does not accept `generator=` in generate().
ALLOW_GENERATOR_FALLBACK = as_bool(os.getenv("ALLOW_GENERATOR_FALLBACK", "1"))

# RNG seed fallback policy:
# - "none": do not derive seed if user does not provide rng_seed (HF-like behavior)
# - "derived": derive a stable seed from prompt token ids (legacy compatibility)
RNG_SEED_FALLBACK = os.getenv("RNG_SEED_FALLBACK", "none").strip().lower()

# -------------------------
# Determinism knob (optional, slower)
# -------------------------
if as_bool(os.getenv("DETERMINISTIC", "0")):
    try:
        torch.use_deterministic_algorithms(True)
        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":16:8")
        import torch.backends.cudnn as cudnn
        cudnn.benchmark = False
        cudnn.deterministic = True
    except Exception as e:
        print(f"[server] DETERMINISTIC setup failed: {e}")

# -------------------------
# Request logging knobs
# -------------------------
# LOG_REQ_BODY=1 enables printing request body; LOG_REQ_BODY_BYTES limits preview bytes.
LOG_REQ_BODY = as_bool(os.getenv("LOG_REQ_BODY", "0"))
LOG_REQ_BODY_BYTES = int(os.getenv("LOG_REQ_BODY_BYTES", "4096"))
