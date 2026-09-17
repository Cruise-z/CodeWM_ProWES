from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import sys

import pytest


CODEGEN_DIR = Path(__file__).resolve().parents[1]
EVAL_DIR = CODEGEN_DIR.parent / "eval"
sys.path.insert(0, str(CODEGEN_DIR))
sys.path.insert(0, str(EVAL_DIR))

import detection_eval
from batch_processors import (
    build_external_processor_config,
    build_external_processor_params,
    build_result_dir,
    validate_external_processor_args,
)
from method_specs import (
    METHOD_CONFIG_SPECS,
    RESERVED_METHODS,
    MethodConfigSpec,
    register_method_config_spec,
    zero_strength_contract_for,
)


METHOD_ARGS = {
    "wllm": {
        "gamma": 0.5,
        "z_threshold": 4.0,
        "ignore_repeated_bigrams": False,
    },
    "sweet": {
        "gamma": 0.5,
        "ET": 0.9,
        "z_threshold": 4.0,
        "ignore_repeated_bigrams": False,
    },
    "waterfall": {
        "id_mu": 42,
        "k_p": 1,
        "n_gram": 2,
        "wm_fn": "fourier",
        "auto_reset": True,
        "detect_mode": "batch",
    },
    "ewd": {
        "gamma": 0.5,
        "hash_key": 15485863,
        "z_threshold": 4.0,
        "prefix_length": 1,
    },
    "stone": {
        "gamma": 0.5,
        "hash_key": 15485863,
        "z_threshold": 4.0,
        "prefix_length": 1,
        "watermark_on_pl": "False",
        "skipping_rule": "all_pl",
    },
    "codeip": {
        "use_pda": True,
        "gamma": 3.0,
        "message_code_len": 20,
        "encode_ratio": 10.0,
        "top_k": 1000,
        "message": [2024],
        "pda_model_path": "/models/codeip-java.pth",
    },
    "mcgmark": {
        "watermark_info": "101010101010",
        "gamma": 0.5,
        "hash_key": 666,
    },
}


def test_registered_methods_expose_explicit_zero_strength_contracts() -> None:
    exact_noop_methods = {"wllm", "sweet", "waterfall", "ewd", "stone"}
    for method in exact_noop_methods:
        assert zero_strength_contract_for(method, METHOD_ARGS[method]) == "exact_noop"

    assert zero_strength_contract_for("mcgmark", METHOD_ARGS["mcgmark"]) == "method_defined"
    assert zero_strength_contract_for("codeip", METHOD_ARGS["codeip"]) == "method_defined"
    assert zero_strength_contract_for(
        "codeip",
        {**METHOD_ARGS["codeip"], "use_pda": False},
    ) == "exact_noop"
    assert zero_strength_contract_for("waterfall", {"wm_fn": "square"}) == "unsupported"


def test_unregistered_method_controls_its_zero_strength_contract() -> None:
    args = {
        "processor_params": {},
        "strength_binding": "beta",
        "zero_strength_contract": "unsupported",
    }
    assert zero_strength_contract_for("futuremark", args) == "unsupported"


def test_reserved_method_is_not_treated_as_an_active_batch_builtin() -> None:
    with pytest.raises(ValueError, match="reserved: not_yet_defined"):
        validate_external_processor_args(
            {
                "processor_names_ext": "evoseal",
                "processor_params": {},
                "strength_binding": "kappa",
            }
        )


def test_reserved_method_activation_must_be_explicit() -> None:
    spec = MethodConfigSpec(
        name="evoseal",
        required_args=frozenset(),
        strength_parameter="kappa",
        parameter_builder=lambda args, strength, language: {"kappa": strength},
    )
    with pytest.raises(ValueError, match="activate_reserved=True"):
        register_method_config_spec(spec)

    register_method_config_spec(spec, activate_reserved=True)
    try:
        assert METHOD_CONFIG_SPECS["evoseal"] is spec
        assert "evoseal" not in RESERVED_METHODS
    finally:
        METHOD_CONFIG_SPECS.pop("evoseal", None)
        RESERVED_METHODS["evoseal"] = "not_yet_defined"


def test_detection_negative_requires_exact_zero_strength_noop() -> None:
    assert detection_eval.validate_detection_negative_control(
        "wllm",
        METHOD_ARGS["wllm"],
        0.0,
    ) == "exact_noop"

    with pytest.raises(ValueError, match="cannot supply a WM-OFF-equivalent negative"):
        detection_eval.validate_detection_negative_control(
            "codeip",
            METHOD_ARGS["codeip"],
            0.0,
        )

    with pytest.raises(ValueError, match="baseline_strength=0.0"):
        detection_eval.validate_detection_negative_control(
            "wllm",
            METHOD_ARGS["wllm"],
            0.5,
        )


def test_unregistered_exact_noop_method_is_not_blocked_by_a_name_whitelist() -> None:
    args = {
        "processor_params": {"alpha": 0.25},
        "strength_binding": "beta",
        "zero_strength_contract": "exact_noop",
    }
    assert detection_eval.validate_detection_negative_control(
        "futuremark",
        args,
        0.0,
    ) == "exact_noop"


def test_detection_scores_are_oriented_before_metric_calculation() -> None:
    assert detection_eval.orient_detection_score(2.5, "higher") == 2.5
    assert detection_eval.orient_detection_score(2.5, "lower") == -2.5
    with pytest.raises(ValueError, match="Unsupported detection score direction"):
        detection_eval.orient_detection_score(2.5, "sideways")


def test_detection_and_batch_use_identical_method_parameter_contracts() -> None:
    for method, method_args in METHOD_ARGS.items():
        batch_args = {"processor_names_ext": method, **method_args}
        batch_params = build_external_processor_params(
            batch_args,
            Decimal("2.5"),
            LANG="python",
        )
        detection_params = detection_eval.build_external_params(
            method,
            method_args,
            2.5,
            "python",
        )

        assert detection_params == {method: batch_params}

def test_codeip_batch_profile_forwards_optional_pda_checkpoint_path() -> None:
    params = build_external_processor_params(
        {"processor_names_ext": "codeip", **METHOD_ARGS["codeip"]},
        Decimal("2.5"),
        LANG="java",
    )
    assert params["use_pda"] is True
    assert params["pda_model_path"] == "/models/codeip-java.pth"


def test_mcgmark_batch_profile_forwards_the_public_watermark_payload() -> None:
    params = build_external_processor_params(
        {"processor_names_ext": "mcgmark", **METHOD_ARGS["mcgmark"]},
        Decimal("2.5"),
        LANG="java",
    )
    assert params["watermark_info"] == "101010101010"


def test_codeip_batch_profile_requires_a_json_boolean_use_pda() -> None:
    with pytest.raises(ValueError, match="JSON boolean"):
        METHOD_CONFIG_SPECS["codeip"].build_params(
            {**METHOD_ARGS["codeip"], "use_pda": "false"},
            2.5,
            "java",
        )


def test_unregistered_method_uses_pass_through_params_and_custom_strength_binding() -> None:
    args = {
        "processor_names_ext": "futuremark",
        "processor_params": {
            "payload": "10110",
            "alpha": 0.25,
        },
        "strength_binding": "beta",
        "result_param_fields": ["payload", "alpha"],
    }

    request_config = build_external_processor_config(
        args,
        Decimal("3.75"),
        LANG="python",
    )

    assert request_config == {
        "external_processor_names": ["futuremark"],
        "external_processor_params": {
            "futuremark": {
                "payload": "10110",
                "alpha": 0.25,
                "beta": 3.75,
            }
        },
    }
    assert detection_eval.build_external_params(
        "futuremark",
        {
            "processor_params": {"payload": "10110", "alpha": 0.25},
            "strength_binding": "beta",
        },
        3.75,
        "python",
    ) == request_config["external_processor_params"]


def test_unregistered_method_result_directory_is_stable_and_descriptive() -> None:
    args = {
        "processor_names_ext": "futuremark",
        "temperature": 0.7,
        "processor_params": {"payload": "10110", "alpha": 0.25},
        "strength_binding": "beta",
        "result_param_fields": ["payload", "alpha"],
    }

    first = build_result_dir(args, "sample", 123, LANG="python")
    second = build_result_dir(args, "sample", 123, LANG="python")

    assert first == second
    assert "futuremark" in first
    assert "payload=10110" in first
    assert "alpha=0.25" in first
    assert "cfg=" in first
