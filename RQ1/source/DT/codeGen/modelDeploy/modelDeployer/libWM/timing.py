"""Timing helpers shared by RQ3-instrumented watermark processors."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import time
from typing import Any, Iterator

import torch


_PROCESSOR_TIMING_ENABLED: ContextVar[bool] = ContextVar(
    "codewm_processor_timing_enabled", default=True
)
_DETECTION_STATE_ENABLED: ContextVar[bool] = ContextVar(
    "codewm_detection_state_enabled", default=True
)


def processor_timing_enabled() -> bool:
    """Return whether request-local per-processor timing is enabled."""

    return bool(_PROCESSOR_TIMING_ENABLED.get())


def detection_state_enabled() -> bool:
    """Return whether generation-coupled detector state may be collected."""

    return bool(_DETECTION_STATE_ENABLED.get())


@contextmanager
def runtime_observation(
    *, processor_timing: bool = True, detection_state: bool = True
) -> Iterator[None]:
    """Configure request-local observation without changing global server state."""

    timing_token = _PROCESSOR_TIMING_ENABLED.set(bool(processor_timing))
    detection_token = _DETECTION_STATE_ENABLED.set(bool(detection_state))
    try:
        yield
    finally:
        _DETECTION_STATE_ENABLED.reset(detection_token)
        _PROCESSOR_TIMING_ENABLED.reset(timing_token)


def synchronize_all_cuda_devices() -> None:
    """Complete queued work on every visible CUDA device."""

    if not torch.cuda.is_available():
        return
    for index in range(torch.cuda.device_count()):
        torch.cuda.synchronize(index)


def synchronized_perf_counter(value: Any = None) -> float:
    """Return a wall-clock timestamp after completing queued CUDA work.

    Synchronization is deliberately outside the measured interval: callers take
    one timestamp immediately before and one immediately after the method-owned
    operation. CPU-only methods retain the ordinary ``perf_counter`` behavior.
    """

    if not processor_timing_enabled():
        return time.perf_counter()

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
