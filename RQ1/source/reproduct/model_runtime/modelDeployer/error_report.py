from __future__ import annotations

import datetime as _datetime
import faulthandler
import os
import sys
import threading
import traceback
from types import TracebackType
from typing import Any


_INSTALLED = False
_REPORTED_EXCEPTION_IDS: set[int] = set()


def verbose_errors_enabled() -> bool:
    value = os.getenv("MODEL_DEPLOYER_VERBOSE_ERRORS", "1").strip().lower()
    return value not in ("0", "false", "no", "off", "")


def install_excepthooks(component: str = "model-deployer") -> None:
    """Install process-level diagnostics for uncaught deployment errors."""
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True

    os.environ.setdefault("TORCH_SHOW_CPP_STACKTRACES", "1")
    try:
        faulthandler.enable(file=sys.stderr, all_threads=True)
    except Exception:
        pass

    def _sys_excepthook(exc_type: type[BaseException], exc: BaseException, tb: TracebackType | None) -> None:
        report_exception(f"unhandled exception in {component}", exc, tb=tb)

    sys.excepthook = _sys_excepthook

    if hasattr(threading, "excepthook"):
        def _thread_excepthook(args: threading.ExceptHookArgs) -> None:
            report_exception(
                f"unhandled thread exception in {component}: {getattr(args.thread, 'name', '<unknown>')}",
                args.exc_value,
                tb=args.exc_traceback,
            )

        threading.excepthook = _thread_excepthook


def report_exception(
    context: str,
    exc: BaseException,
    *,
    tb: TracebackType | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Print a complete error report to the deployment terminal."""
    if not verbose_errors_enabled():
        return
    os.environ.setdefault("TORCH_SHOW_CPP_STACKTRACES", "1")

    exc_id = id(exc)
    if exc_id in _REPORTED_EXCEPTION_IDS:
        _flush_streams()
        return
    _REPORTED_EXCEPTION_IDS.add(exc_id)

    stream = sys.stderr
    timestamp = _datetime.datetime.now().isoformat(timespec="seconds")
    print("", file=stream)
    print("=" * 88, file=stream)
    print(f"[model-deployer error] {timestamp} | {context}", file=stream)
    print(f"type: {exc.__class__.__module__}.{exc.__class__.__name__}", file=stream)
    print(f"message: {exc}", file=stream)
    if extra:
        print("extra:", file=stream)
        for key, value in extra.items():
            print(f"  {key}: {value}", file=stream)
    print("runtime:", file=stream)
    for key, value in _runtime_snapshot().items():
        print(f"  {key}: {value}", file=stream)
    hints = _diagnostic_hints(exc)
    if hints:
        print("hints:", file=stream)
        for hint in hints:
            print(f"  - {hint}", file=stream)
    print("-" * 88, file=stream)
    traceback.print_exception(type(exc), exc, tb or exc.__traceback__, file=stream, chain=True)
    print("=" * 88, file=stream)
    print("", file=stream)
    _flush_streams()


def _runtime_snapshot() -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "pid": os.getpid(),
        "cwd": os.getcwd(),
        "argv": " ".join(sys.argv),
        "python": sys.version.replace("\n", " "),
        "CUDA_VISIBLE_DEVICES": os.getenv("CUDA_VISIBLE_DEVICES"),
        "GPU_MAX_MEMORY": os.getenv("GPU_MAX_MEMORY"),
        "PYTORCH_CUDA_ALLOC_CONF": os.getenv("PYTORCH_CUDA_ALLOC_CONF"),
        "TORCH_SHOW_CPP_STACKTRACES": os.getenv("TORCH_SHOW_CPP_STACKTRACES"),
    }

    torch_mod = sys.modules.get("torch")
    if torch_mod is not None:
        try:
            snapshot["torch_version"] = getattr(torch_mod, "__version__", None)
            snapshot["cuda_available"] = torch_mod.cuda.is_available()
            snapshot["cuda_device_count"] = torch_mod.cuda.device_count()
            if torch_mod.cuda.is_available():
                try:
                    current = torch_mod.cuda.current_device()
                    snapshot["cuda_current_device"] = current
                    snapshot["cuda_device_name"] = torch_mod.cuda.get_device_name(current)
                    snapshot["cuda_memory_allocated"] = torch_mod.cuda.memory_allocated(current)
                    snapshot["cuda_memory_reserved"] = torch_mod.cuda.memory_reserved(current)
                except Exception as exc:
                    snapshot["cuda_snapshot_error"] = f"{exc.__class__.__name__}: {exc}"
        except Exception as exc:
            snapshot["torch_snapshot_error"] = f"{exc.__class__.__name__}: {exc}"

    return snapshot


def _diagnostic_hints(exc: BaseException) -> list[str]:
    text = f"{exc.__class__.__name__}: {exc}".lower()
    hints: list[str] = []
    if "device-side assert" in text:
        hints.append("For CUDA device-side asserts, rerun with CUDA_LAUNCH_BLOCKING=1 to get a more accurate traceback.")
        hints.append("If the error appears in a logits processor, check candidate token ids against model/tokenizer vocab sizes.")
    if "out of memory" in text or "cuda_oom" in text:
        hints.append("For CUDA OOM, reduce max_tokens/batch size or set GPU_MAX_MEMORY/PYTORCH_CUDA_ALLOC_CONF before startup.")
    if "index out of range" in text or "embedding" in text:
        hints.append("Index/embedding errors often indicate token ids exceed the checkpoint/model embedding vocabulary.")
    return hints


def _flush_streams() -> None:
    try:
        sys.stdout.flush()
    except Exception:
        pass
    try:
        sys.stderr.flush()
    except Exception:
        pass
