"""Default manual batch run launcher.

Editable experiment parameters live in a local JSON file so routine test runs
do not require editing Python modules.
"""

from __future__ import annotations

import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
from typing import Any, Optional, Union

from batch_processors import (
    _is_no_external_processor,
    _processor_name,
    validate_external_processor_args,
)


CODEGEN_DIR = Path(__file__).resolve().parent
DT_ROOT = CODEGEN_DIR.parent
DEFAULT_CONFIG_PATH = CODEGEN_DIR / "batchConfig.json"


def _resolve_config_path(config_path: Optional[Union[str, Path]]) -> Path:
    raw_path = config_path or os.environ.get("BATCH_RUN_CONFIG") or DEFAULT_CONFIG_PATH
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = CODEGEN_DIR / path
    return path.resolve()


def _resolve_path(value: str, *, base_dir: Path = CODEGEN_DIR) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def load_batch_run_config(config_path: Optional[Union[str, Path]] = None) -> dict:
    path = _resolve_config_path(config_path)
    with path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    config["_config_path"] = str(path)
    return config


def _validate_experiment_args(args: dict[str, Any], *, label: str) -> str:
    for key in ("temperature", "max_tokens"):
        if key not in args:
            raise ValueError(f"{label} is missing required args.{key}")

    processor = _processor_name(args)
    if not _is_no_external_processor(processor):
        try:
            validate_external_processor_args(args)
        except ValueError as exc:
            raise ValueError(f"{label}: {exc}") from exc
    return processor


def resolve_batch_experiments(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize legacy single-run and multi-experiment batch configurations."""
    shared_args = config.get("args") or {}
    if not isinstance(shared_args, dict):
        raise ValueError("top-level args must be a JSON object")

    raw_experiments = config.get("experiments")
    if raw_experiments is None:
        args = deepcopy(shared_args)
        processor = _validate_experiment_args(args, label="args")
        rng_seed = config.get("rng_seed")
        return [
            {
                "name": processor,
                "processor": processor,
                "args": args,
                "wmS_config": deepcopy(config.get("wmS_config")),
                "rng_seed": None if rng_seed is None else int(rng_seed),
            }
        ]

    if not isinstance(raw_experiments, list) or not raw_experiments:
        raise ValueError("experiments must be a non-empty JSON array")

    resolved: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for index, raw_experiment in enumerate(raw_experiments, start=1):
        label = f"experiments[{index - 1}]"
        if not isinstance(raw_experiment, dict):
            raise ValueError(f"{label} must be a JSON object")

        enabled = raw_experiment.get("enabled", True)
        if not isinstance(enabled, bool):
            raise ValueError(f"{label}.enabled must be a boolean")
        if not enabled:
            continue

        experiment_args = raw_experiment.get("args") or {}
        if not isinstance(experiment_args, dict):
            raise ValueError(f"{label}.args must be a JSON object")
        args = deepcopy(shared_args)
        args.update(deepcopy(experiment_args))
        processor = _validate_experiment_args(args, label=label)

        name = str(raw_experiment.get("name") or processor or f"experiment-{index}").strip()
        if not name:
            raise ValueError(f"{label}.name must not be empty")
        normalized_name = name.casefold()
        if normalized_name in seen_names:
            raise ValueError(f"duplicate enabled experiment name: {name!r}")
        seen_names.add(normalized_name)
        args["_experiment_name"] = name

        wmS_config = raw_experiment.get("wmS_config", config.get("wmS_config"))
        if wmS_config is not None and not isinstance(wmS_config, dict):
            raise ValueError(f"{label}.wmS_config must be a JSON object")
        rng_seed = raw_experiment.get("rng_seed", config.get("rng_seed"))

        resolved.append(
            {
                "name": name,
                "processor": processor,
                "args": args,
                "wmS_config": deepcopy(wmS_config),
                "rng_seed": None if rng_seed is None else int(rng_seed),
            }
        )

    if not resolved:
        raise ValueError("experiments does not contain any enabled entries")
    return resolved


def run_default_batch(config_path: Optional[Union[str, Path]] = None) -> None:
    from batch_runner import codeGenBatch, selectRngSeed, validateRngSeed

    config = load_batch_run_config(config_path)
    experiments = resolve_batch_experiments(config)
    paths = config.get("paths", {})

    project_name = config["project_name"]
    srcPath = str(_resolve_path(paths["srcPath"]))
    workspacePath = str(_resolve_path(paths["workspacePath"]))
    resPath = str(_resolve_path(paths["resPath"]))
    testFilePath = (DT_ROOT / "dockerTest" / "test_podman.sh").resolve()

    def seed_probe_args_for(experiment: dict[str, Any]) -> dict[str, Any]:
        probe_args = {
            key: experiment["args"][key]
            for key in ("temperature", "max_tokens", "top_p")
            if key in experiment["args"]
        }
        configured_probe_args = config.get("seed_probe_args")
        if configured_probe_args is not None:
            if not isinstance(configured_probe_args, dict):
                raise ValueError("seed_probe_args must be a JSON object")
            probe_args.update(configured_probe_args)
        for key in ("temperature", "max_tokens"):
            if key not in probe_args:
                raise ValueError(f"seed_probe_args is missing required {key}")
        return probe_args

    selected_rng_seed: Optional[int] = None
    missing_seed_experiments = [
        experiment for experiment in experiments if experiment["rng_seed"] is None
    ]
    if missing_seed_experiments:
        seed_probe_args = seed_probe_args_for(missing_seed_experiments[0])
        selected_rng_seed = asyncio.run(
            selectRngSeed(
                project_name,
                srcPath,
                workspacePath,
                testFilePath,
                seed_probe_args,
            )
        )
        print(f"[batch] selected_rng_seed={selected_rng_seed}")

    resolved_runs: list[tuple[dict[str, Any], int]] = []
    for experiment in experiments:
        rng_seed = experiment["rng_seed"]
        if rng_seed is None:
            if selected_rng_seed is None:
                raise RuntimeError("seed probe did not return a seed")
            rng_seed = selected_rng_seed
        resolved_runs.append((experiment, int(rng_seed)))

    # selectRngSeed already ran the same WM-OFF preflight for its returned seed.
    validated_seeds = (
        {int(selected_rng_seed)} if selected_rng_seed is not None else set()
    )
    for experiment, rng_seed in resolved_runs:
        if rng_seed in validated_seeds:
            continue
        print(f"[batch] WM-OFF baseline preflight start: rng_seed={rng_seed}")
        preflight = asyncio.run(
            validateRngSeed(
                rng_seed,
                project_name,
                srcPath,
                workspacePath,
                testFilePath,
                seed_probe_args_for(experiment),
            )
        )
        if not preflight["passed"]:
            raise RuntimeError(
                "WM-OFF baseline preflight failed before watermark experiments: "
                f"rng_seed={rng_seed} "
                f"generation_complete={preflight['generation_complete']} "
                f"docker_return_code={preflight['docker_return_code']}"
            )
        validated_seeds.add(rng_seed)
        print(f"[batch] WM-OFF baseline preflight passed: rng_seed={rng_seed}")

    continue_on_error = config.get("continue_on_error", False)
    if not isinstance(continue_on_error, bool):
        raise ValueError("continue_on_error must be a boolean")

    failures: list[tuple[str, Exception]] = []
    wm_off_reference_cache: dict[str, dict[str, Any]] = {}
    total = len(resolved_runs)
    for index, (experiment, rng_seed) in enumerate(resolved_runs, start=1):
        print(
            f"[batch] experiment {index}/{total} start: "
            f"name={experiment['name']} processor={experiment['processor']} rng_seed={rng_seed}"
        )
        try:
            asyncio.run(
                codeGenBatch(
                    rng_seed,
                    project_name,
                    srcPath,
                    workspacePath,
                    resPath,
                    testFilePath,
                    experiment["args"],
                    experiment["wmS_config"],
                    wm_off_reference_cache=wm_off_reference_cache,
                )
            )
        except Exception as exc:
            failures.append((experiment["name"], exc))
            print(
                f"[batch] experiment {index}/{total} failed: "
                f"name={experiment['name']} error={exc.__class__.__name__}: {exc}"
            )
            if not continue_on_error:
                raise
        else:
            print(f"[batch] experiment {index}/{total} complete: name={experiment['name']}")

    if failures:
        failed_names = ", ".join(name for name, _ in failures)
        raise RuntimeError(
            f"{len(failures)} batch experiment(s) failed: {failed_names}"
        ) from failures[0][1]


if __name__ == "__main__":
    run_default_batch()
