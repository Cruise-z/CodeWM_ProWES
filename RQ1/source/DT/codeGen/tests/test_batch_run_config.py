from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import sys
import types

import pytest


CODEGEN_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODEGEN_DIR))

import batch_run_config
from batch_processors import build_external_processor_config, build_result_dir
from batch_snapshots import strength_values


EXAMPLE_PATH = CODEGEN_DIR / "batchConfig.multi.example.json"


def _load_example() -> dict:
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


def test_legacy_single_args_config_remains_supported() -> None:
    config = {
        "rng_seed": 123,
        "wmS_config": {"values": ["2.0"]},
        "args": {
            "temperature": 0.7,
            "max_tokens": 64,
            "processor_names_ext": "waterfall",
            "id_mu": 42,
            "k_p": 1,
            "n_gram": 2,
            "wm_fn": "fourier",
            "auto_reset": True,
            "detect_mode": "batch",
        },
    }

    experiments = batch_run_config.resolve_batch_experiments(config)

    assert len(experiments) == 1
    assert experiments[0]["name"] == "waterfall"
    assert experiments[0]["rng_seed"] == 123
    assert "_experiment_name" not in experiments[0]["args"]


def test_example_resolves_all_non_evoseal_processors() -> None:
    config = _load_example()
    experiments = batch_run_config.resolve_batch_experiments(config)

    assert [experiment["processor"] for experiment in experiments] == [
        "wllm",
        "sweet",
        "waterfall",
        "ewd",
        "stone",
        "codeip",
        "mcgmark",
    ]
    assert len({experiment["name"] for experiment in experiments}) == len(experiments)
    assert all(experiment["wmS_config"] == config["wmS_config"] for experiment in experiments)

    result_dirs = set()
    for experiment in experiments:
        strength = Decimal(str(experiment["wmS_config"]["start"]))
        request_config = build_external_processor_config(
            experiment["args"],
            strength,
            LANG="python",
        )
        assert request_config["external_processor_names"] == [experiment["processor"]]
        result_dirs.add(
            build_result_dir(
                experiment["args"],
                "example",
                123,
                LANG="python",
            )
        )
    assert len(result_dirs) == len(experiments)


def test_experiment_strength_config_overrides_top_level_range() -> None:
    config = _load_example()
    override = {"start": "11.1", "step": "0.1", "end": "11.3"}
    config["experiments"][0]["wmS_config"] = override

    experiments = batch_run_config.resolve_batch_experiments(config)

    assert experiments[0]["wmS_config"] == override
    assert experiments[1]["wmS_config"] == config["wmS_config"]


def test_strength_range_includes_start_step_and_end() -> None:
    assert strength_values(
        {"start": "11.1", "step": "0.1", "end": "11.3"}
    ) == (
        Decimal("11.1"),
        Decimal("11.2"),
        Decimal("11.3"),
    )


def test_duplicate_enabled_experiment_names_are_rejected() -> None:
    config = _load_example()
    duplicate = deepcopy(config["experiments"][0])
    config["experiments"].append(duplicate)

    with pytest.raises(ValueError, match="duplicate enabled experiment name"):
        batch_run_config.resolve_batch_experiments(config)


def test_missing_processor_specific_args_are_rejected_before_dispatch() -> None:
    config = {
        "args": {"temperature": 0.7, "max_tokens": 64},
        "experiments": [
            {
                "name": "incomplete-sweet",
                "args": {"processor_names_ext": "sweet", "gamma": 0.5},
            }
        ],
    }

    with pytest.raises(ValueError, match=r"missing required args: ET, z_threshold"):
        batch_run_config.resolve_batch_experiments(config)


def test_future_method_pass_through_config_resolves_without_framework_registration() -> None:
    config = {
        "rng_seed": 123,
        "wmS_config": {"values": ["1.5"]},
        "args": {"temperature": 0.7, "max_tokens": 64},
        "experiments": [
            {
                "name": "futuremark-beta",
                "args": {
                    "processor_names_ext": "futuremark",
                    "processor_params": {"payload": "10110"},
                    "strength_binding": "beta",
                    "result_param_fields": ["payload"],
                },
            }
        ],
    }

    experiments = batch_run_config.resolve_batch_experiments(config)

    assert experiments[0]["processor"] == "futuremark"
    assert experiments[0]["args"]["processor_params"] == {"payload": "10110"}
    assert experiments[0]["args"]["strength_binding"] == "beta"


def test_run_default_batch_dispatches_every_enabled_experiment(monkeypatch) -> None:
    config = _load_example()
    config.pop("rng_seed")
    calls: list[tuple] = []

    async def fake_select_rng_seed(*args):
        calls.append(("seed", *args))
        return 777

    async def unexpected_validate_rng_seed(*args):
        raise AssertionError("the selected random seed was already validated")

    async def fake_code_gen_batch(*args, **kwargs):
        calls.append(("batch", *args, kwargs))

    fake_batch_runner = types.ModuleType("batch_runner")
    fake_batch_runner.selectRngSeed = fake_select_rng_seed
    fake_batch_runner.validateRngSeed = unexpected_validate_rng_seed
    fake_batch_runner.codeGenBatch = fake_code_gen_batch
    monkeypatch.setitem(sys.modules, "batch_runner", fake_batch_runner)
    monkeypatch.setattr(batch_run_config, "load_batch_run_config", lambda _: config)

    batch_run_config.run_default_batch("unused.json")

    batch_calls = [call for call in calls if call[0] == "batch"]
    assert len([call for call in calls if call[0] == "seed"]) == 1
    assert len(batch_calls) == len(config["experiments"])
    assert all(call[1] == 777 for call in batch_calls)
    assert [call[7]["processor_names_ext"] for call in batch_calls] == [
        experiment["args"]["processor_names_ext"] for experiment in config["experiments"]
    ]
    reference_caches = [call[-1]["wm_off_reference_cache"] for call in batch_calls]
    assert all(cache is reference_caches[0] for cache in reference_caches)


def test_explicit_top_level_seed_runs_one_exact_unwatermarked_preflight(monkeypatch) -> None:
    config = _load_example()
    calls: list[tuple] = []

    async def unexpected_select_rng_seed(*args):
        calls.append(("seed", *args))
        raise AssertionError("an explicit seed must not be replaced")

    async def fake_validate_rng_seed(*args):
        calls.append(("preflight", *args))
        return {
            "passed": True,
            "generation_complete": True,
            "docker_return_code": 0,
        }

    async def fake_code_gen_batch(*args, **kwargs):
        calls.append(("batch", *args, kwargs))

    fake_batch_runner = types.ModuleType("batch_runner")
    fake_batch_runner.selectRngSeed = unexpected_select_rng_seed
    fake_batch_runner.validateRngSeed = fake_validate_rng_seed
    fake_batch_runner.codeGenBatch = fake_code_gen_batch
    monkeypatch.setitem(sys.modules, "batch_runner", fake_batch_runner)
    monkeypatch.setattr(batch_run_config, "load_batch_run_config", lambda _: config)

    batch_run_config.run_default_batch("unused.json")

    assert not [call for call in calls if call[0] == "seed"]
    preflight_calls = [call for call in calls if call[0] == "preflight"]
    assert len(preflight_calls) == 1
    assert preflight_calls[0][1] == config["rng_seed"]
    assert preflight_calls[0][6] == {
        "temperature": config["seed_probe_args"]["temperature"],
        "max_tokens": config["seed_probe_args"]["max_tokens"],
        "top_p": config["args"]["top_p"],
    }
    batch_calls = [call for call in calls if call[0] == "batch"]
    assert len(batch_calls) == len(config["experiments"])
    assert all(call[1] == config["rng_seed"] for call in batch_calls)


def test_seed_probe_only_fills_experiments_without_a_seed(monkeypatch) -> None:
    config = _load_example()
    config["experiments"][0]["rng_seed"] = 456
    config.pop("rng_seed")
    calls: list[tuple] = []

    async def fake_select_rng_seed(*args):
        calls.append(("seed", *args))
        return 777

    async def fake_validate_rng_seed(*args):
        calls.append(("preflight", *args))
        return {
            "passed": True,
            "generation_complete": True,
            "docker_return_code": 0,
        }

    async def fake_code_gen_batch(*args, **kwargs):
        calls.append(("batch", *args, kwargs))

    fake_batch_runner = types.ModuleType("batch_runner")
    fake_batch_runner.selectRngSeed = fake_select_rng_seed
    fake_batch_runner.validateRngSeed = fake_validate_rng_seed
    fake_batch_runner.codeGenBatch = fake_code_gen_batch
    monkeypatch.setitem(sys.modules, "batch_runner", fake_batch_runner)
    monkeypatch.setattr(batch_run_config, "load_batch_run_config", lambda _: config)

    batch_run_config.run_default_batch("unused.json")

    assert len([call for call in calls if call[0] == "seed"]) == 1
    preflight_calls = [call for call in calls if call[0] == "preflight"]
    assert len(preflight_calls) == 1
    assert preflight_calls[0][1] == 456
    batch_calls = [call for call in calls if call[0] == "batch"]
    assert batch_calls[0][1] == 456
    assert all(call[1] == 777 for call in batch_calls[1:])


def test_distinct_explicit_seeds_are_each_preflighted_once(monkeypatch) -> None:
    config = _load_example()
    config["experiments"][0]["rng_seed"] = 456
    calls: list[tuple] = []

    async def unexpected_select_rng_seed(*args):
        raise AssertionError("all experiments have explicit seeds")

    async def fake_validate_rng_seed(*args):
        calls.append(("preflight", *args))
        return {
            "passed": True,
            "generation_complete": True,
            "docker_return_code": 0,
        }

    async def fake_code_gen_batch(*args, **kwargs):
        calls.append(("batch", *args, kwargs))

    fake_batch_runner = types.ModuleType("batch_runner")
    fake_batch_runner.selectRngSeed = unexpected_select_rng_seed
    fake_batch_runner.validateRngSeed = fake_validate_rng_seed
    fake_batch_runner.codeGenBatch = fake_code_gen_batch
    monkeypatch.setitem(sys.modules, "batch_runner", fake_batch_runner)
    monkeypatch.setattr(batch_run_config, "load_batch_run_config", lambda _: config)

    batch_run_config.run_default_batch("unused.json")

    assert [call[1] for call in calls if call[0] == "preflight"] == [
        456,
        config["rng_seed"],
    ]
    assert len([call for call in calls if call[0] == "batch"]) == len(
        config["experiments"]
    )


def test_failed_explicit_seed_preflight_aborts_before_watermark_dispatch(monkeypatch) -> None:
    config = _load_example()
    batch_calls: list[tuple] = []

    async def unexpected_select_rng_seed(*args):
        raise AssertionError("all experiments have explicit seeds")

    async def fake_validate_rng_seed(*args):
        return {
            "passed": False,
            "generation_complete": False,
            "docker_return_code": None,
        }

    async def fake_code_gen_batch(*args, **kwargs):
        batch_calls.append((*args, kwargs))

    fake_batch_runner = types.ModuleType("batch_runner")
    fake_batch_runner.selectRngSeed = unexpected_select_rng_seed
    fake_batch_runner.validateRngSeed = fake_validate_rng_seed
    fake_batch_runner.codeGenBatch = fake_code_gen_batch
    monkeypatch.setitem(sys.modules, "batch_runner", fake_batch_runner)
    monkeypatch.setattr(batch_run_config, "load_batch_run_config", lambda _: config)

    with pytest.raises(RuntimeError, match="WM-OFF baseline preflight failed"):
        batch_run_config.run_default_batch("unused.json")

    assert batch_calls == []


def test_continue_on_error_runs_remaining_experiments(monkeypatch) -> None:
    config = _load_example()
    config.pop("rng_seed")
    dispatched: list[str] = []

    async def fake_select_rng_seed(*args):
        return 777

    async def unexpected_validate_rng_seed(*args):
        raise AssertionError("the selected random seed was already validated")

    async def fake_code_gen_batch(*args, **kwargs):
        processor = args[6]["processor_names_ext"]
        dispatched.append(processor)
        if processor == "sweet":
            raise RuntimeError("synthetic failure")

    fake_batch_runner = types.ModuleType("batch_runner")
    fake_batch_runner.selectRngSeed = fake_select_rng_seed
    fake_batch_runner.validateRngSeed = unexpected_validate_rng_seed
    fake_batch_runner.codeGenBatch = fake_code_gen_batch
    monkeypatch.setitem(sys.modules, "batch_runner", fake_batch_runner)
    monkeypatch.setattr(batch_run_config, "load_batch_run_config", lambda _: config)

    with pytest.raises(RuntimeError, match="sweet-default"):
        batch_run_config.run_default_batch("unused.json")

    assert dispatched == [
        experiment["args"]["processor_names_ext"] for experiment in config["experiments"]
    ]
