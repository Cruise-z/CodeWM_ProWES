"""CPU-only contract tests for the non-intrusive v2 observation path."""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys

import torch


MODEL_DEPLOYER = (
    Path(__file__).resolve().parents[2]
    / "RQ1/source/reproduct/model_runtime/modelDeployer"
)
sys.path.insert(0, str(MODEL_DEPLOYER))

from libWM.standalone_detection import detect_text  # noqa: E402
from libWM.timing import (  # noqa: E402
    detection_state_enabled,
    processor_timing_enabled,
    runtime_observation,
)


def test_runtime_observation_is_request_scoped_and_propagates_to_thread() -> None:
    assert processor_timing_enabled() is True
    assert detection_state_enabled() is True

    async def inspect_thread() -> tuple[bool, bool]:
        return await asyncio.to_thread(
            lambda: (processor_timing_enabled(), detection_state_enabled())
        )

    with runtime_observation(processor_timing=False, detection_state=False):
        assert asyncio.run(inspect_thread()) == (False, False)

    assert processor_timing_enabled() is True
    assert detection_state_enabled() is True


class _Tokenizer:
    def __call__(self, text: str, **_: object):
        return {"input_ids": torch.tensor([[ord(char) for char in text]])}


class _WLLMDummy:
    _codewm_method = "wllm"

    def __init__(self) -> None:
        self._cache_full_ids = None
        self._cache_prefix_len = None
        self._cache_prev_len = None

    def detect_last(self):
        return {
            "detector_input_tokens": int(self._cache_full_ids.numel()),
            "generation_prefix_len": int(self._cache_prefix_len),
        }


def test_standalone_detection_builds_state_from_final_text() -> None:
    processor = _WLLMDummy()
    result, count = detect_text(processor, _Tokenizer(), "final")

    assert count == 5
    assert result == {
        "detector_input_tokens": 5,
        "generation_prefix_len": 0,
    }
