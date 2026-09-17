"""Timing helpers shared by RQ3-instrumented watermark processors."""

from __future__ import annotations

import time
from typing import Any

import torch


def synchronized_perf_counter(value: Any = None) -> float:
    """Return a wall-clock timestamp after completing queued CUDA work.

    Synchronization is deliberately outside the measured interval: callers take
    one timestamp immediately before and one immediately after the method-owned
    operation. CPU-only methods retain the ordinary ``perf_counter`` behavior.
    """

    try:
        device = getattr(value, "device", None)
        if device is not None and getattr(device, "type", None) == "cuda":
            torch.cuda.synchronize(device)
        elif value is None and torch.cuda.is_available():
            torch.cuda.synchronize()
    except Exception:
        # Timing instrumentation must never alter watermark behavior.
        pass
    return time.perf_counter()
