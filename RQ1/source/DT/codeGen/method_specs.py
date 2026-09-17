"""Lightweight watermark method configuration contracts.

This module intentionally does not import model runtime code. Batch generation,
detection evaluation, and future method adapters can therefore share one
parameter/strength contract without loading a model.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import importlib
import json
import os
from typing import Any, Callable, Literal, Mapping, Optional, Union


ParamBuilder = Callable[[Mapping[str, Any], float, Optional[str]], dict[str, Any]]
ZeroStrengthContract = Literal["exact_noop", "method_defined", "unsupported"]
ZERO_STRENGTH_CONTRACTS = frozenset({"exact_noop", "method_defined", "unsupported"})
ZeroStrengthResolver = Callable[[Mapping[str, Any]], ZeroStrengthContract]


@dataclass(frozen=True)
class MethodConfigSpec:
    name: str
    required_args: frozenset[str]
    strength_parameter: Optional[str]
    parameter_builder: ParamBuilder
    result_fields: tuple[tuple[str, str], ...] = ()
    zero_strength_contract: Union[ZeroStrengthContract, ZeroStrengthResolver] = "method_defined"

    def __post_init__(self) -> None:
        if (
            not callable(self.zero_strength_contract)
            and self.zero_strength_contract not in ZERO_STRENGTH_CONTRACTS
        ):
            raise ValueError(
                f"unsupported zero-strength contract: {self.zero_strength_contract!r}"
            )

    def build_params(
        self,
        args: Mapping[str, Any],
        strength: float,
        language: Optional[str],
    ) -> dict[str, Any]:
        return self.parameter_builder(args, float(strength), language)


def _require_language(language: Optional[str], method: str) -> str:
    if language is None:
        raise ValueError(f"processor_names_ext='{method}' requires LANG")
    return str(language)


def _build_wllm(args: Mapping[str, Any], strength: float, language: Optional[str]) -> dict[str, Any]:
    return {
        "gamma": args["gamma"],
        "delta": strength,
        "z_threshold": args["z_threshold"],
        "ignore_repeated_bigrams": args.get("ignore_repeated_bigrams", False),
    }


def _build_sweet(args: Mapping[str, Any], strength: float, language: Optional[str]) -> dict[str, Any]:
    return {
        "gamma": args["gamma"],
        "delta": strength,
        "entropy_threshold": args["ET"],
        "z_threshold": args["z_threshold"],
        "ignore_repeated_bigrams": args.get("ignore_repeated_bigrams", False),
    }


def _build_waterfall(args: Mapping[str, Any], strength: float, language: Optional[str]) -> dict[str, Any]:
    return {
        "id_mu": args["id_mu"],
        "k_p": args["k_p"],
        "kappa": strength,
        "n_gram": args["n_gram"],
        "wm_fn": args["wm_fn"],
        "auto_reset": args.get("auto_reset", True),
        "detect_mode": args.get("detect_mode", "batch"),
    }


def _waterfall_zero_strength_contract(
    args: Mapping[str, Any],
) -> ZeroStrengthContract:
    return "exact_noop" if str(args.get("wm_fn", "fourier")).lower() == "fourier" else "unsupported"


def _build_ewd(args: Mapping[str, Any], strength: float, language: Optional[str]) -> dict[str, Any]:
    return {
        "gamma": args["gamma"],
        "delta": strength,
        "hash_key": args["hash_key"],
        "z_threshold": args["z_threshold"],
        "prefix_length": args["prefix_length"],
    }


def _build_stone(args: Mapping[str, Any], strength: float, language: Optional[str]) -> dict[str, Any]:
    return {
        "gamma": args["gamma"],
        "delta": strength,
        "hash_key": args["hash_key"],
        "z_threshold": args["z_threshold"],
        "prefix_length": args["prefix_length"],
        "language": _require_language(language, "stone"),
        "watermark_on_pl": args.get("watermark_on_pl", "False"),
        "skipping_rule": args.get("skipping_rule", "all_pl"),
    }


def _resolve_codeip_use_pda(args: Mapping[str, Any]) -> bool:
    if "use_pda" not in args:
        raise ValueError("CodeIP batch configuration requires use_pda")
    use_pda = args["use_pda"]
    if not isinstance(use_pda, bool):
        raise ValueError("CodeIP use_pda must be a JSON boolean")
    return use_pda


def _build_codeip(args: Mapping[str, Any], strength: float, language: Optional[str]) -> dict[str, Any]:
    params = {
        "use_pda": _resolve_codeip_use_pda(args),
        "language": _require_language(language, "codeip"),
        "delta": strength,
        "gamma": args["gamma"],
        "message_code_len": args["message_code_len"],
        "encode_ratio": args["encode_ratio"],
        "top_k": args["top_k"],
        "message": args["message"],
    }
    if args.get("pda_model_path") is not None:
        params["pda_model_path"] = args["pda_model_path"]
    return params


def _codeip_zero_strength_contract(
    args: Mapping[str, Any],
) -> ZeroStrengthContract:
    return "method_defined" if _resolve_codeip_use_pda(args) else "exact_noop"


def _build_mcgmark(args: Mapping[str, Any], strength: float, language: Optional[str]) -> dict[str, Any]:
    return {
        "watermark_info": args["watermark_info"],
        "gamma": args["gamma"],
        "delta": strength,
        "hash_key": args["hash_key"],
    }


METHOD_CONFIG_SPECS: dict[str, MethodConfigSpec] = {
    "wllm": MethodConfigSpec(
        "wllm", frozenset({"gamma", "z_threshold"}), "delta", _build_wllm,
        (("gamma", "gamma"),),
        "exact_noop",
    ),
    "sweet": MethodConfigSpec(
        "sweet", frozenset({"gamma", "ET", "z_threshold"}), "delta", _build_sweet,
        (("gamma", "gamma"), ("ET", "ET")),
        "exact_noop",
    ),
    "waterfall": MethodConfigSpec(
        "waterfall",
        frozenset({"id_mu", "k_p", "n_gram", "wm_fn", "auto_reset", "detect_mode"}),
        "kappa",
        _build_waterfall,
        (("idMu", "id_mu"), ("kP", "k_p"), ("nGram", "n_gram"), ("wmFn", "wm_fn")),
        _waterfall_zero_strength_contract,
    ),
    "ewd": MethodConfigSpec(
        "ewd",
        frozenset({"gamma", "hash_key", "z_threshold", "prefix_length"}),
        "delta",
        _build_ewd,
        (("gamma", "gamma"), ("hashKey", "hash_key"), ("prefixLen", "prefix_length")),
        "exact_noop",
    ),
    "stone": MethodConfigSpec(
        "stone",
        frozenset({
            "gamma", "hash_key", "z_threshold", "prefix_length", "watermark_on_pl", "skipping_rule"
        }),
        "delta",
        _build_stone,
        (("gamma", "gamma"), ("hashKey", "hash_key"), ("prefixLen", "prefix_length")),
        "exact_noop",
    ),
    "codeip": MethodConfigSpec(
        "codeip",
        frozenset({"use_pda", "gamma", "message_code_len", "encode_ratio", "top_k", "message"}),
        "delta",
        _build_codeip,
        (
            ("gamma", "gamma"),
            ("usePDA", "use_pda"),
            ("messageLen", "message_code_len"),
            ("encodeRatio", "encode_ratio"),
            ("topK", "top_k"),
        ),
        _codeip_zero_strength_contract,
    ),
    "mcgmark": MethodConfigSpec(
        "mcgmark", frozenset({"watermark_info", "gamma", "hash_key"}), "delta", _build_mcgmark,
        (("watermarkInfo", "watermark_info"), ("gamma", "gamma"), ("hashKey", "hash_key")),
        "method_defined",
    ),
}

RESERVED_METHODS: dict[str, str] = {
    "evoseal": "not_yet_defined",
}


def register_method_config_spec(
    spec: MethodConfigSpec,
    *,
    activate_reserved: bool = False,
) -> None:
    """Register a lightweight spec from a future method integration module."""
    if not isinstance(spec, MethodConfigSpec):
        raise TypeError("spec must be a MethodConfigSpec")
    name = str(spec.name).strip().lower()
    if not name:
        raise ValueError("method spec name must not be empty")
    if name in RESERVED_METHODS:
        if not activate_reserved:
            raise ValueError(
                f"method {name!r} is reserved: {RESERVED_METHODS[name]}; "
                "registration requires activate_reserved=True"
            )
        RESERVED_METHODS.pop(name)
    METHOD_CONFIG_SPECS[name] = spec


def generic_method_config(args: Mapping[str, Any]) -> tuple[dict[str, Any], Optional[str]]:
    """Read an unregistered future method's pass-through configuration."""
    params = args.get("processor_params")
    if not isinstance(params, dict):
        raise ValueError(
            "unregistered processor requires args.processor_params as a JSON object"
        )
    if "strength_binding" not in args:
        raise ValueError(
            "unregistered processor requires args.strength_binding; use null for no strength parameter"
        )
    binding = args.get("strength_binding")
    if binding is not None and (not isinstance(binding, str) or not binding.strip()):
        raise ValueError("args.strength_binding must be a non-empty string or null")
    return deepcopy(params), None if binding is None else binding.strip()


def build_method_params(
    method: str,
    args: Mapping[str, Any],
    strength: float,
    language: Optional[str],
) -> dict[str, Any]:
    normalized = str(method).strip().lower()
    spec = METHOD_CONFIG_SPECS.get(normalized)
    if spec is not None:
        return spec.build_params(args, strength, language)

    params, strength_binding = generic_method_config(args)
    if strength_binding is not None:
        params[strength_binding] = float(strength)
    return params


def result_fields_for(method: str, args: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    spec = METHOD_CONFIG_SPECS.get(str(method).strip().lower())
    if spec is not None:
        return spec.result_fields

    configured = args.get("result_param_fields", ())
    if not isinstance(configured, (list, tuple)) or not all(
        isinstance(item, str) and item.strip() for item in configured
    ):
        raise ValueError("args.result_param_fields must be an array of parameter names")
    return tuple((item.strip(), item.strip()) for item in configured)


def strength_parameter_for(method: str, args: Mapping[str, Any]) -> Optional[str]:
    spec = METHOD_CONFIG_SPECS.get(str(method).strip().lower())
    if spec is not None:
        return spec.strength_parameter
    _, strength_binding = generic_method_config(args)
    return strength_binding


def zero_strength_contract_for(
    method: str,
    args: Mapping[str, Any],
) -> ZeroStrengthContract:
    spec = METHOD_CONFIG_SPECS.get(str(method).strip().lower())
    if spec is not None:
        resolved = (
            spec.zero_strength_contract(args)
            if callable(spec.zero_strength_contract)
            else spec.zero_strength_contract
        )
        if resolved not in ZERO_STRENGTH_CONTRACTS:
            raise ValueError(
                f"method {spec.name!r} resolved an unsupported zero-strength contract: "
                f"{resolved!r}"
            )
        return resolved

    raw_contract = str(args.get("zero_strength_contract", "method_defined")).strip().lower()
    if raw_contract not in ZERO_STRENGTH_CONTRACTS:
        supported = ", ".join(sorted(ZERO_STRENGTH_CONTRACTS))
        raise ValueError(
            f"args.zero_strength_contract must be one of: {supported}"
        )
    return raw_contract  # type: ignore[return-value]


def generic_config_digest(args: Mapping[str, Any]) -> str:
    params, strength_binding = generic_method_config(args)
    payload = {
        "processor_params": params,
        "strength_binding": strength_binding,
        "zero_strength_contract": zero_strength_contract_for("<generic>", args),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def load_method_spec_extensions() -> None:
    """Load optional lightweight config specs without importing model runtime."""
    configured = os.getenv("CODEWM_METHOD_SPEC_MODULES", "")
    for module_name in (name.strip() for name in configured.split(",")):
        if module_name:
            importlib.import_module(module_name)


load_method_spec_extensions()
