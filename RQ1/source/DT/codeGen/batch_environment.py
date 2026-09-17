"""Environment setup for batch code generation."""

from __future__ import annotations

import os


def configure_default_proxy() -> None:
    """Apply the same default proxy environment used by the historical script."""
    os.environ["HTTPS_PROXY"] = os.environ.get("HTTPS_PROXY", "http://127.0.0.1:7890")
    os.environ["HTTP_PROXY"] = os.environ.get("HTTP_PROXY", "http://127.0.0.1:7890")
    os.environ["ALL_PROXY"] = os.environ.get("ALL_PROXY", os.environ["HTTPS_PROXY"])

    no_proxy = set(filter(None, os.environ.get("NO_PROXY", "").split(",")))
    no_proxy.update({"127.0.0.1", "localhost", "::1"})
    os.environ["NO_PROXY"] = ",".join(no_proxy)
    os.environ["no_proxy"] = os.environ["NO_PROXY"]
