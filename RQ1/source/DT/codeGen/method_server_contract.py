"""Lightweight client for the deployed method registry and capability contract."""

from __future__ import annotations

import json
import os
from typing import Any, Mapping, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, Request, build_opener, urlopen


DEFAULT_MODEL_SERVER_URL = "http://127.0.0.1:8000/v1"


def processor_catalog_url(base_url: Optional[str] = None) -> str:
    base = (
        base_url
        or os.getenv("CODEWM_MODEL_SERVER_URL")
        or DEFAULT_MODEL_SERVER_URL
    ).strip().rstrip("/")
    if not base:
        raise ValueError("model server URL must not be empty")
    return f"{base}/_processors"


def fetch_method_catalog(
    base_url: Optional[str] = None,
    *,
    timeout_sec: float = 10.0,
) -> dict[str, Any]:
    url = processor_catalog_url(base_url)
    request = Request(url, headers={"Accept": "application/json"})
    try:
        hostname = (urlsplit(url).hostname or "").lower()
        if hostname in {"localhost", "127.0.0.1", "::1"}:
            response_context = build_opener(ProxyHandler({})).open(
                request,
                timeout=float(timeout_sec),
            )
        else:
            response_context = urlopen(request, timeout=float(timeout_sec))
        with response_context as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, OSError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"failed to read model method catalog from {url}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"model method catalog at {url} is not a JSON object")
    return payload


def require_deployed_method(
    catalog: Mapping[str, Any],
    method: str,
    *,
    require_detection: bool = False,
) -> Mapping[str, Any]:
    name = str(method).strip().lower()
    plugins = catalog.get("method_plugins") or ()
    if name not in plugins:
        raise ValueError(
            f"method {name!r} is not an active deployed plugin; active={sorted(plugins)}"
        )

    contracts = catalog.get("method_contracts")
    if not isinstance(contracts, Mapping) or not isinstance(
        contracts.get(name), Mapping
    ):
        raise ValueError(f"deployed method {name!r} has no method contract metadata")
    contract = contracts[name]
    if require_detection:
        detection = contract.get("detection")
        if not isinstance(detection, Mapping):
            raise ValueError(f"deployed method {name!r} has no detection contract")
        if detection.get("mode") != "processor_state":
            raise ValueError(
                f"deployed method {name!r} does not support generation-coupled "
                f"detection: {detection.get('mode')!r}"
            )
        fields = detection.get("score_fields")
        if not isinstance(fields, list) or not fields:
            raise ValueError(
                f"deployed method {name!r} detection contract has no score fields"
            )
        if detection.get("score_direction") not in {"higher", "lower"}:
            raise ValueError(
                f"deployed method {name!r} has invalid detection score direction: "
                f"{detection.get('score_direction')!r}"
            )
        if contract.get("final_generation_evidence") is not True:
            raise ValueError(
                f"deployed method {name!r} does not guarantee final generation evidence"
            )
    return contract
