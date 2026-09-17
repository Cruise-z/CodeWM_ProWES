from __future__ import annotations

from pathlib import Path
import sys
import json

import pytest


CODEGEN_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODEGEN_DIR))

import method_server_contract
from method_server_contract import (
    fetch_method_catalog,
    processor_catalog_url,
    require_deployed_method,
)


CATALOG = {
    "method_plugins": ["futuremark", "mcgmark"],
    "method_contracts": {
        "futuremark": {
            "parameters": {"accepted": ["alpha", "beta"], "required": ["alpha"]},
            "detection": {
                "mode": "processor_state",
                "score_fields": ["z_score"],
                "score_direction": "higher",
                "independent_text_detection": False,
            },
            "final_generation_evidence": True,
        },
        "mcgmark": {
            "parameters": {"accepted": ["delta"], "required": []},
            "detection": {
                "mode": "unavailable",
                "score_fields": [],
                "score_direction": None,
                "independent_text_detection": False,
            },
            "final_generation_evidence": False,
        },
    },
}


def test_processor_catalog_url_uses_the_openai_v1_base() -> None:
    assert processor_catalog_url("http://localhost:9000/v1/") == (
        "http://localhost:9000/v1/_processors"
    )


def test_loopback_catalog_bypasses_environment_proxy(monkeypatch) -> None:
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return json.dumps(CATALOG).encode("utf-8")

    class Opener:
        def open(self, request, timeout):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            return Response()

    def fake_build_opener(proxy_handler):
        captured["proxies"] = proxy_handler.proxies
        return Opener()

    monkeypatch.setattr(method_server_contract, "build_opener", fake_build_opener)
    monkeypatch.setattr(
        method_server_contract,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("loopback catalog must not use the environment proxy opener")
        ),
    )

    assert fetch_method_catalog("http://127.0.0.1:8000/v1", timeout_sec=3.0) == CATALOG
    assert captured == {
        "proxies": {},
        "url": "http://127.0.0.1:8000/v1/_processors",
        "timeout": 3.0,
    }


def test_remote_catalog_is_the_active_method_authority() -> None:
    contract = require_deployed_method(
        CATALOG,
        "futuremark",
        require_detection=True,
    )
    assert contract["detection"]["score_fields"] == ["z_score"]

    with pytest.raises(ValueError, match="not an active deployed plugin"):
        require_deployed_method(CATALOG, "unknown")

    with pytest.raises(ValueError, match="does not support"):
        require_deployed_method(CATALOG, "mcgmark", require_detection=True)

    incomplete = json.loads(json.dumps(CATALOG))
    incomplete["method_contracts"]["futuremark"]["final_generation_evidence"] = False
    with pytest.raises(ValueError, match="does not guarantee final generation evidence"):
        require_deployed_method(incomplete, "futuremark", require_detection=True)
