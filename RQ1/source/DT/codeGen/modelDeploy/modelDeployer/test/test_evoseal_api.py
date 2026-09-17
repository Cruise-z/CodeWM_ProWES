"""Small manual smoke test for the EvoSeal model-deployer integration."""

from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen


BASE_URL = os.getenv("OPENAI_API_BASE", "http://127.0.0.1:8000/v1").rstrip("/")
MODEL = os.getenv("OPENAI_MODEL_NAME", "Qwen/Qwen2.5-Coder-32B-Instruct")
TIMEOUT_S = float(os.getenv("EVOSEAL_TEST_TIMEOUT_S", "600"))

os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost,::1")
os.environ.setdefault("no_proxy", "127.0.0.1,localhost,::1")


def _request(path: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if data is None else "POST",
    )
    with urlopen(request, timeout=TIMEOUT_S) as response:
        return json.load(response)


def main() -> None:
    processors = _request("/_processors")
    builders = processors.get("external_builders", [])
    if "evoseal" not in builders:
        raise RuntimeError(f"evoseal is not registered; external_builders={builders}")

    response = _request(
        "/chat/completions",
        {
            "model": MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": "Write a short Python function that returns the square of an integer.",
                }
            ],
            "temperature": 0.7,
            "rng_seed": 123456,
            "max_tokens": int(os.getenv("EVOSEAL_TEST_MAX_TOKENS", "64")),
            "external_processor_names": ["evoseal"],
            "external_processor_params": {
                "evoseal": {
                    "id_mu": 42,
                    "k_p": 1,
                    "kappa": 2.0,
                    "n_gram": 2,
                    "wm_fn": "fourier",
                    "auto_reset": True,
                    "detect_mode": "batch",
                    "watermark_domain_policy": "legacy_base_vocab",
                    "enable_vocab_diagnostics": False,
                }
            },
            "watermark_detect": os.getenv("EVOSEAL_TEST_DETECT", "0") == "1",
        },
    )
    print(json.dumps(response, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
