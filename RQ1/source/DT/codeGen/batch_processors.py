"""External watermark processor parameter and result-directory configuration."""

from __future__ import annotations

import hashlib
from decimal import Decimal
from pathlib import Path
from typing import Optional, Union

from batch_utils import (
    _arg_value,
    _as_bool,
    _shorten_path_component,
)
from method_specs import (
    METHOD_CONFIG_SPECS,
    RESERVED_METHODS,
    build_method_params,
    generic_config_digest,
    generic_method_config,
    result_fields_for,
)

def _processor_name(args: dict) -> str:
    return str(args.get("processor_names_ext", "none") or "none").strip().lower()


def _is_no_external_processor(processor: object) -> bool:
    return str(processor or "").strip().lower() in {"", "none", "no", "null", "baseline", "no_watermark"}


def validate_external_processor_args(args: dict) -> str:
    processor = _processor_name(args)
    if _is_no_external_processor(processor):
        return processor
    if processor in RESERVED_METHODS:
        raise ValueError(
            f"processor_names_ext={processor!r} is reserved: "
            f"{RESERVED_METHODS[processor]}"
        )
    if processor not in METHOD_CONFIG_SPECS:
        generic_method_config(args)
        return processor

    missing = sorted(
        key for key in METHOD_CONFIG_SPECS[processor].required_args if key not in args
    )
    if missing:
        raise ValueError(
            f"processor_names_ext={processor!r} is missing required args: {', '.join(missing)}"
        )
    return processor


def _iteration_rng_seed(base_seed: int, wmS: Decimal, processor: str, args: dict) -> int:
    if not _is_no_external_processor(processor):
        return int(base_seed)
    vary_seed = _as_bool(
        _arg_value(args, "no_watermark_vary_seed", "baseline_vary_seed", default=True),
        default=True,
    )
    if not vary_seed:
        return int(base_seed)
    if wmS == Decimal("0"):
        return int(base_seed)
    digest = hashlib.sha1(f"{base_seed}:{wmS}".encode("utf-8")).hexdigest()
    offset = int(digest[:8], 16)
    seed = (int(base_seed) + offset) % (2**32 - 1)
    return seed or 1


def build_external_processor_params(args, wmS, LANG=None, project_root: Optional[Union[str, Path]] = None):
    processor = validate_external_processor_args(args)
    return build_method_params(processor, args, float(wmS), LANG)


def _require_lang(LANG, processor):
    if LANG is None:
        raise ValueError(f"processor_names_ext='{processor}' requires LANG")
    return LANG


def build_external_processor_config(args, wmS, LANG=None, project_root: Optional[Union[str, Path]] = None):
    processor = _processor_name(args)
    if _is_no_external_processor(processor):
        return {
            "external_processor_names": [],
            "external_processor_params": {},
        }

    return {
        "external_processor_names": [processor],
        "external_processor_params": {
            processor: build_external_processor_params(
                args=args,
                wmS=wmS,
                LANG=LANG,
                project_root=project_root,
            )
        },
    }

def build_result_dir(args, project_name, rng_seed, LANG=None, project_root: Optional[Union[str, Path]] = None):
    processor = _processor_name(args)

    parts = [
        project_name,
        processor,
    ]
    experiment_name = str(args.get("_experiment_name") or "").strip()
    if experiment_name:
        parts.append(f"exp={experiment_name}")
    parts.extend(
        [
            f"T={args['temperature']}",
            f"rngS={rng_seed}",
        ]
    )

    if _is_no_external_processor(processor):
        return _shorten_path_component("_".join(parts))

    processor_fields = result_fields_for(processor, args)
    processor_params = args.get("processor_params") or {}
    for label, key in processor_fields:
        value = args[key] if key in args else processor_params[key]
        parts.append(f"{label}={value}")

    if processor not in METHOD_CONFIG_SPECS:
        parts.append(f"cfg={generic_config_digest(args)}")

    if processor == "stone":
        if LANG is None:
            raise ValueError("processor_names_ext='stone' requires LANG")
        parts.append(f"lang={LANG}")

    return _shorten_path_component("_".join(parts))
