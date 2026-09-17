"""Batch generation orchestration."""

from __future__ import annotations

import json
import os
import re
import sys
from decimal import Decimal
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Literal, Optional

from batch_environment import configure_default_proxy

configure_default_proxy()

from agentCodeGen import codeGen, make_seed
from aiAPI import *
from batch_docker import docker_exec
from batch_file_ops import find_path, shellDelete, shellPaste
from batch_processors import (
    _arg_value,
    _as_bool,
    _is_no_external_processor,
    _iteration_rng_seed,
    _processor_name,
    build_external_processor_config,
    build_result_dir,
)
from batch_snapshots import (
    calculate_diversity_metrics,
    get_programming_language,
    hash_code_snapshot,
    remove_leading_h2_line,
    snapshot_code_files,
    strength_values,
)
from batch_utils import MAX_RESULT_DIR_COMPONENT_BYTES, read_file
from batch_zero_strength import (
    compare_zero_strength_reference,
    generation_response_manifest,
    initial_zero_strength_audit,
    wm_off_reference_cache_key,
)
from method_specs import strength_parameter_for, zero_strength_contract_for


async def validateRngSeed(
    rng_seed: int,
    project_name: str,
    srcPath: str,
    workspacePath: str,
    testFilePath: Path,
    args: dict[str, Any],
    lang: Optional[Literal["cpp", "java", "python"]] = None,
) -> dict[str, Any]:
    """Run one exact-seed WM-OFF generation and validate its generated project."""
    repoPath = Path(f"{srcPath}/{project_name}").resolve()

    try:
        LANG = get_programming_language(repoPath)
    except Exception:
        if lang is None:
            raise RuntimeError("Unable to auto-detect language; please pass lang explicitly.")
        LANG = lang
    LANG = LANG.lower()

    ckptPath = Path(f"{srcPath}/storage").resolve()
    codeFilePath = Path(f"{workspacePath}/{project_name}/{project_name}").resolve()
    xargs = {
        "temperature": args["temperature"],
        "max_tokens": args["max_tokens"],
        "rng_seed": int(rng_seed),
        "internal_processor_names": [],
        "external_processor_names": [],
        "external_processor_params": {},
        "watermark_detect": False,
    }
    if "top_p" in args:
        xargs["top_p"] = args["top_p"]

    shellDelete(workspacePath, dry_run=False)
    shellPaste([repoPath, ckptPath], workspacePath)
    generation_report = await codeGen(
        project_name,
        xargs,
        abort_on_truncation=True,
    )
    if generation_report is None:
        generation_report = {
            "request_succeeded": True,
            "generation_complete": True,
            "truncated_files": [],
        }
    if not isinstance(generation_report, dict):
        raise TypeError("codeGen must return a generation report dictionary")

    generation_complete = bool(generation_report.get("generation_complete"))
    result: dict[str, Any] = {
        "rng_seed": int(rng_seed),
        "passed": False,
        "generation_complete": generation_complete,
        "docker_return_code": None,
        "generation_report": generation_report,
        "generation_response_manifest": generation_response_manifest(generation_report),
        "source_snapshot": None,
        "source_snapshot_hash": None,
    }
    if not generation_complete:
        return result

    source_snapshot, retCode, _ = docker_exec(
        {"": ""},
        codeFilePath,
        testFilePath,
        LANG,
        f"rngS={rng_seed}-wmoff-preflight",
    )
    if not isinstance(source_snapshot, dict):
        raise TypeError("docker_exec must return a source snapshot dictionary")
    result["source_snapshot"] = source_snapshot
    result["source_snapshot_hash"] = hash_code_snapshot(source_snapshot)
    result["docker_return_code"] = retCode
    result["passed"] = retCode == 0
    return result


async def selectRngSeed(
    project_name: str,
    srcPath: str,
    workspacePath: str,
    testFilePath: Path,
    args: dict[str, Any],
    lang: Optional[Literal["cpp", "java", "python"]] = None,
) -> Optional[int]:
    print("[batch] rng_seed not configured; starting random WM-OFF seed selection")
    attempt = 0
    while True:
        attempt += 1
        seed = make_seed(32)
        print(f"[batch] WM-OFF seed attempt {attempt} start: rng_seed={seed}")
        try:
            result = await validateRngSeed(
                seed,
                project_name,
                srcPath,
                workspacePath,
                testFilePath,
                args,
                lang=lang,
            )
        except Exception as exc:
            print(
                f"[batch] WM-OFF seed attempt {attempt} error: rng_seed={seed} "
                f"error={exc.__class__.__name__}: {exc}"
            )
            raise
        if result["passed"]:
            print(
                f"[batch] WM-OFF seed attempt {attempt} passed: "
                f"rng_seed={seed} generation_complete=True docker_return_code=0"
            )
            return seed
        print(
            f"[batch] WM-OFF seed attempt {attempt} failed: rng_seed={seed} "
            f"generation_complete={result['generation_complete']} "
            f"docker_return_code={result['docker_return_code']}; retrying"
        )

filterPrompt = """
Read the log above and output *ONLY* one [label] (no other text, eg: "[Pass]", "[Build Error]", etc):
 [Build Error]: The project fails during build or compilation related steps before tests can pass. Examples: Java Maven compile failure, C++ compile/link failure, dependency/build setup failure that prevents a successful build;
 [Test Error]: The project builds enough to run tests, but the required test step fails. Examples: failing assertions, test process errors, or `ctest` / `pytest` / `mvn test` failures caused by tests rather than by compilation;
 [Packaging Error]: The project passes tests, but fails when creating the required runnable artifact. Examples: `mvn package fails`, `Python zipapp creation fails`, or `no expected packaged executable/artifact is produced`;
 [Runtime Error]: The project passes tests and packaging, but the packaged artifact fails during the short execution check. Examples: the app crashes on startup, exits with an error, or cannot run successfully for the required short period;
 [Pass]: The project follows the protocol, passes the required tests, produces the expected packaged artifact, and the packaged artifact can start successfully in the short run check.
"""

async def codeGenBatch(
    rng_seed: int,
    project_name: str,
    srcPath: str,
    workspacePath: str,
    resPath: str,
    testFilePath: Path,
    args: dict[str, Any],
    wmS_config: Optional[dict[str, Any]] = None,
    lang: Optional[Literal["cpp", "java", "python"]] = None,
    wm_off_reference_cache: Optional[dict[str, dict[str, Any]]] = None,
):
    client = Client("/home/zhaorz/.config/Personal_config/config_aiAPI.ini", "paid")

    repoPath = Path(f"{srcPath}/{project_name}").resolve()

    # Determine the programming language
    try:
        LANG = get_programming_language(repoPath)
    except:
        if lang is None:
            raise RuntimeError("Unable to auto-detect language; please pass lang explicitly.")
        LANG = lang
    LANG = LANG.lower()

    ckptPath = Path(f"{srcPath}/storage").resolve()
    codeFilePath = Path(f"{workspacePath}/{project_name}/{project_name}").resolve()

    configured_strengths = strength_values(wmS_config)
    runtime_args = dict(args)
    processor_type = _processor_name(args)
    zero_strength_requested = (
        Decimal("0") in configured_strengths
        and not _is_no_external_processor(processor_type)
    )
    zero_strength_contract = (
        zero_strength_contract_for(processor_type, args)
        if not _is_no_external_processor(processor_type)
        else "not_applicable"
    )
    if zero_strength_requested and zero_strength_contract == "unsupported":
        raise ValueError(
            f"processor_names_ext={processor_type!r} does not support wmS=0"
        )
    zero_strength_audit = initial_zero_strength_audit(
        requested=zero_strength_requested,
        contract=zero_strength_contract,
        rng_seed=rng_seed,
    )
    zero_strength_reference: Optional[dict[str, Any]] = None

    prev_code_snapshot: Optional[dict[str, str]] = None

    # --- NEW: batch-level res aggregation (only increment when res is actually produced) ---
    ALLOWED_LABELS = ("[Build Error]", "[Test Error]", "[Packaging Error]", "[Runtime Error]", "[Pass]")
    GENERATION_INCOMPLETE_LABEL = "[Generation Incomplete]"
    TEST_RESULT_UNCLASSIFIED_LABEL = "[Test Result Unclassified]"
    batch_res_counts: dict[str, int] = {
        label: 0
        for label in (
            *ALLOWED_LABELS,
            GENERATION_INCOMPLETE_LABEL,
            TEST_RESULT_UNCLASSIFIED_LABEL,
        )
    }
    batch_tested_count = 0
    batch_skipped_count = 0
    batch_wms_results: list[dict[str, Any]] = []
    batch_diversity_records: list[dict[str, Any]] = []
    seen_snapshot_hashes: set[str] = set()

    def _norm_label(x: Any) -> Optional[str]:
        s = str(x).strip().lower().rstrip(" .:;!?\n\t")
        scored = sorted(
            ((label, SequenceMatcher(None, s, label.lower()).ratio()) for label in ALLOWED_LABELS),
            key=lambda t: t[1],
            reverse=True,
        )
        best_label, best_score = scored[0]
        if best_score < 0.6:
            print(f"[WARN] Low-confidence label mapping: raw={x!r}, mapped={best_label!r}, score={best_score:.3f}")
            return None
        return best_label

    def _format_batch_test_stats() -> str:
        classified_count = sum(batch_res_counts[label] for label in ALLOWED_LABELS)
        denom = max(classified_count, 1)
        label_parts = [
            f"{label}={batch_res_counts[label]}({batch_res_counts[label] / denom * 100:.1f}%)"
            for label in ALLOWED_LABELS
        ]
        return (
            f"tested={batch_tested_count} "
            f"classified={classified_count} "
            f"test_result_unclassified={batch_res_counts[TEST_RESULT_UNCLASSIFIED_LABEL]} "
            f"skipped={batch_skipped_count} | "
            f"generation_incomplete={batch_res_counts[GENERATION_INCOMPLETE_LABEL]} | "
            + " ".join(label_parts)
        )

    def _print_batch_test_stats(wmS_value: Decimal, last_status: str) -> None:
        processor_type = _processor_name(args)
        print(
            f"[INFO] Test stats after wmS={wmS_value} "
            f"processor={processor_type} last={last_status}: {_format_batch_test_stats()}"
        )

    result_dir = build_result_dir(args, project_name, rng_seed, LANG, project_root=codeFilePath)
    out_dir = Path(f"{resPath}/{result_dir}").resolve()
    summary_path = out_dir / f"{project_name}_batch_summary_rngS={rng_seed}.json"
    progress_path = out_dir / f"{project_name}_batch_progress_rngS={rng_seed}.jsonl"
    diversity_path = out_dir / f"{project_name}_generation_diversity_rngS={rng_seed}.jsonl"
    def _batch_summary_payload() -> dict[str, Any]:
        return {
            "project_name": project_name,
            "experiment_name": args.get("_experiment_name"),
            "rng_seed": rng_seed,
            "language": LANG,
            "processor": processor_type,
            "zero_strength_audit": dict(zero_strength_audit),
            "no_watermark_vary_seed": (
                _as_bool(_arg_value(args, "no_watermark_vary_seed", "baseline_vary_seed", default=True), default=True)
                if _is_no_external_processor(processor_type)
                else False
            ),
            "result_dir": result_dir,
            "result_dir_component_max_bytes": MAX_RESULT_DIR_COMPONENT_BYTES,
            "counts": dict(batch_res_counts),
            "tested_count": batch_tested_count,
            "skipped_count": batch_skipped_count,
            "progress_jsonl": str(progress_path),
            "generation_diversity_jsonl": str(diversity_path),
            "configured_strength_count": len(configured_strengths),
            "processed_strength_count": len(batch_wms_results),
            "diversity_metrics": calculate_diversity_metrics(batch_wms_results),
            "diversity_records": list(batch_diversity_records),
            "wmS_results": list(batch_wms_results),
        }

    def _write_batch_summary() -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = summary_path.with_suffix(summary_path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(_batch_summary_payload(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp_path.replace(summary_path)

    def _append_batch_progress(entry: dict[str, Any]) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        with progress_path.open("a", encoding="utf-8") as pf:
            pf.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _append_diversity_record(entry: dict[str, Any]) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        with diversity_path.open("a", encoding="utf-8") as df:
            df.write(json.dumps(entry, ensure_ascii=False) + "\n")

    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        progress_path.write_text("", encoding="utf-8")
        diversity_path.write_text("", encoding="utf-8")
        _write_batch_summary()
        print(f"[INFO] Batch summary initialized at {summary_path}")
        print(f"[INFO] Batch progress JSONL initialized at {progress_path}")
        print(f"[INFO] Generation diversity JSONL initialized at {diversity_path}")
    except Exception as e:
        print(f"[WARN] Failed to initialize batch progress files: {e}")

    if zero_strength_requested:
        reference_cache = (
            wm_off_reference_cache
            if wm_off_reference_cache is not None
            else {}
        )
        reference_key, reference_generation_config = wm_off_reference_cache_key(
            project_name=project_name,
            repo_path=repoPath,
            rng_seed=rng_seed,
            language=LANG,
            args=runtime_args,
        )
        zero_strength_audit.update(
            {
                "reference_cache_key": reference_key,
                "reference_generation_config": reference_generation_config,
            }
        )
        reference_artifact_root = (
            out_dir / f"wm_off_reference_rngS={rng_seed}"
        ).resolve()
        reference_artifact_root.mkdir(parents=True, exist_ok=True)
        cached_reference = reference_cache.get(reference_key)
        if cached_reference is not None:
            cached_artifact_value = cached_reference.get("artifact_path")
            if not cached_artifact_value:
                raise RuntimeError("cached WM-OFF reference has no artifact path")
            cached_artifact_path = Path(str(cached_artifact_value)).resolve()
            if not cached_artifact_path.is_dir():
                raise RuntimeError(
                    "cached WM-OFF reference artifact is unavailable: "
                    f"{cached_artifact_path}"
                )
            if cached_artifact_path.parent != reference_artifact_root:
                shellDelete(reference_artifact_root, dry_run=False)
                shellPaste([cached_artifact_path], reference_artifact_root)
            zero_strength_reference = dict(cached_reference)
            zero_strength_reference["artifact_path"] = str(
                (reference_artifact_root / cached_artifact_path.name).resolve()
            )
            zero_strength_audit["reference_cache_hit"] = True
            print(
                f"[INFO] Reusing exact-config WM-OFF reference for "
                f"processor={processor_type} rng_seed={rng_seed} key={reference_key[:12]}"
            )
        else:
            shellDelete(reference_artifact_root, dry_run=False)
            print(
                f"[INFO] Building exact-config WM-OFF reference for zero-strength audit: "
                f"processor={processor_type} rng_seed={rng_seed} key={reference_key[:12]}"
            )
            reference_result = await validateRngSeed(
                rng_seed,
                project_name,
                srcPath,
                workspacePath,
                testFilePath,
                runtime_args,
                lang=LANG,
            )
            if not reference_result["passed"]:
                zero_strength_audit.update(
                    {
                        "reference_status": "failed",
                        "comparison_status": "not_run",
                        "contract_status": "not_evaluated",
                    }
                )
                _write_batch_summary()
                raise RuntimeError(
                    "exact-config WM-OFF reference failed before zero-strength audit: "
                    f"rng_seed={rng_seed} "
                    f"generation_complete={reference_result['generation_complete']} "
                    f"docker_return_code={reference_result['docker_return_code']}"
                )

            shellPaste([codeFilePath], reference_artifact_root)
            reference_result = dict(reference_result)
            reference_result["artifact_path"] = str(
                (reference_artifact_root / codeFilePath.name).resolve()
            )
            reference_cache[reference_key] = reference_result
            zero_strength_reference = reference_result

        if zero_strength_reference is None:
            raise RuntimeError("zero-strength WM-OFF reference was not initialized")
        reference_snapshot = zero_strength_reference.get("source_snapshot")
        if not isinstance(reference_snapshot, dict) or not reference_snapshot:
            raise RuntimeError("zero-strength WM-OFF reference has no source snapshot")
        zero_strength_audit.update(
            {
                "reference_status": "ready",
                "reference_source_snapshot_hash": zero_strength_reference.get(
                    "source_snapshot_hash"
                ),
                "reference_response_manifest": list(
                    zero_strength_reference.get("generation_response_manifest") or []
                ),
                "reference_artifact_path": zero_strength_reference.get("artifact_path"),
            }
        )
        _write_batch_summary()

    for strength_index, wmS in enumerate(configured_strengths, start=1):
        print(
            f"[INFO] Strength {strength_index}/{len(configured_strengths)} start: "
            f"processor={processor_type} wmS={wmS}"
        )
        last_status = "unclassified"
        last_label: Optional[str] = None
        last_log_path: Optional[str] = None
        last_classifier_output: Optional[str] = None
        iteration_rng_seed = _iteration_rng_seed(rng_seed, wmS, processor_type, runtime_args)
        xargs = {
            "temperature": args["temperature"],
            "max_tokens": args["max_tokens"],
            # "parallel": args["parallel"],
            "rng_seed": iteration_rng_seed,
            "internal_processor_names": [],
            "watermark_detect": runtime_args.get("watermark_detect", not _is_no_external_processor(processor_type)),
            **build_external_processor_config(
                args=runtime_args,
                wmS=wmS,
                LANG=LANG,
                project_root=codeFilePath,
            ),
        }
        if "top_p" in runtime_args:
            xargs["top_p"] = runtime_args["top_p"]

        processor_params = (
            xargs.get("external_processor_params", {}).get(processor_type, {})
            if processor_type
            else {}
        )
        strength_parameter = (
            None
            if _is_no_external_processor(processor_type)
            else strength_parameter_for(processor_type, args)
        )
        effective_strength = (
            processor_params.get(strength_parameter)
            if strength_parameter is not None
            else None
        )
        if processor_type == "waterfall":
            experiment_profile = str(processor_params.get("wm_fn", "fourier"))
            effective_kappa = processor_params.get("kappa")
        elif _is_no_external_processor(processor_type):
            experiment_profile = "none"
            effective_kappa = None
        else:
            experiment_profile = str(_arg_value(args, "profile", default=processor_type))
            effective_kappa = processor_params.get("kappa", processor_params.get("delta"))

        diversity_record: dict[str, Any] = {
            "method": processor_type,
            "profile": experiment_profile,
            "wm_strength": str(wmS),
            "effective_kappa": effective_kappa,
            "strength_parameter": strength_parameter,
            "effective_strength": effective_strength,
            "rng_seed": iteration_rng_seed,
            "generation_succeeded": False,
            "complete_source_snapshot": {},
            "source_snapshot_hash": None,
            "same_as_previous_snapshot": False,
            "already_seen_snapshot": False,
            "build_skipped_due_to_unchanged_snapshot": False,
        }

        # 1) Clear the workspace
        shellDelete(workspacePath, dry_run=False)
        # 2) Copy project code into the workspace
        shellPaste([repoPath, ckptPath], workspacePath)
        # 3) Invoke code generation
        try:
            generation_report = await codeGen(
                project_name,
                xargs,
                abort_on_truncation=True,
            )
            if generation_report is None:
                generation_report = {
                    "request_succeeded": True,
                    "generation_complete": True,
                    "aborted_on_truncation": False,
                    "expected_file_count": None,
                    "completed_file_count": None,
                    "saved_file_count": None,
                    "files": [],
                    "truncated_files": [],
                }
            if not isinstance(generation_report, dict):
                raise TypeError("codeGen must return a generation report dictionary")
            truncated_files = list(generation_report.get("truncated_files") or [])
            generation_complete = bool(generation_report.get("generation_complete"))
            diversity_record.update(
                {
                    "generation_succeeded": generation_complete,
                    "generation_request_succeeded": bool(
                        generation_report.get("request_succeeded")
                    ),
                    "generation_complete": generation_complete,
                    "generation_aborted_on_truncation": bool(
                        generation_report.get("aborted_on_truncation")
                    ),
                    "truncated_files": truncated_files,
                    "generation_files": list(generation_report.get("files") or []),
                    "generation_response_manifest": generation_response_manifest(
                        generation_report
                    ),
                }
            )
        except Exception as exc:
            if wmS == Decimal("0") and zero_strength_requested:
                zero_strength_audit.update(
                    {
                        "comparison_status": "generation_error",
                        "contract_status": "not_evaluated",
                    }
                )
            diversity_record["generation_error"] = f"{exc.__class__.__name__}: {exc}"
            batch_diversity_records.append(dict(diversity_record))
            batch_wms_results.append(dict(diversity_record))
            try:
                _append_diversity_record(diversity_record)
                _write_batch_summary()
            except Exception as write_exc:
                print(f"[WARN] Failed to record generation failure for wmS={wmS}: {write_exc}")
            raise

        # 4) Build output directory for this wmS
        destPath = Path(f"{resPath}/{result_dir}/{project_name}_{wmS}").resolve()
        os.makedirs(destPath, exist_ok=True)

        if not generation_complete:
            batch_res_counts[GENERATION_INCOMPLETE_LABEL] += 1
            if wmS == Decimal("0") and zero_strength_requested:
                zero_strength_audit.update(
                    {
                        "comparison_status": "generation_incomplete",
                        "contract_status": "not_evaluated",
                    }
                )
                diversity_record["zero_strength_comparison"] = {
                    "status": "generation_incomplete",
                    "contract": zero_strength_contract,
                    "source_exact_match": None,
                    "generated_text_exact_match": None,
                    "finish_reasons_exact_match": None,
                    "contract_status": "not_evaluated",
                }
            shellPaste([codeFilePath], destPath)
            generation_status_path = destPath / "generation_status.json"
            generation_status_path.write_text(
                json.dumps(
                    {
                        "project_name": project_name,
                        "processor": processor_type,
                        "wmS": str(wmS),
                        "rng_seed": iteration_rng_seed,
                        "generation_report": generation_report,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            if truncated_files:
                last_status = "generation_truncated"
            else:
                last_status = "generation_incomplete"

            diversity_record["partial_artifacts_preserved"] = True
            diversity_record["generation_status_path"] = str(generation_status_path)
            batch_diversity_records.append(dict(diversity_record))
            _append_diversity_record(diversity_record)

            wmS_result = {
                **diversity_record,
                "wmS": str(wmS),
                "processor": processor_type,
                "rng_seed": iteration_rng_seed,
                "tested": False,
                "skipped": False,
                "ret_code": None,
                "result_label": None,
                "status": last_status,
                "classification_log": None,
                "classifier_output": None,
                "result_path": str(destPath),
            }
            batch_wms_results.append(wmS_result)
            try:
                _append_batch_progress(wmS_result)
                _write_batch_summary()
            except Exception as exc:
                print(f"[WARN] Failed to record incomplete generation for wmS={wmS}: {exc}")
            _print_batch_test_stats(wmS, last_status)
            print(
                f"[WARN] wmS={wmS} generation was incomplete; partial artifacts saved to "
                f"{destPath}; continuing to the next configured strength"
            )
            continue

        # 5) Record the normalized source snapshot before the duplicate/build decision.
        try:
            remove_leading_h2_line(codeFilePath)
            curr_code_snapshot = snapshot_code_files(codeFilePath, LANG)
            source_snapshot_hash = hash_code_snapshot(curr_code_snapshot)
        except Exception as exc:
            diversity_record["snapshot_error"] = f"{exc.__class__.__name__}: {exc}"
            batch_diversity_records.append(dict(diversity_record))
            batch_wms_results.append(dict(diversity_record))
            try:
                _append_diversity_record(diversity_record)
                _write_batch_summary()
            except Exception as write_exc:
                print(f"[WARN] Failed to record snapshot failure for wmS={wmS}: {write_exc}")
            raise

        same_as_previous = (
            prev_code_snapshot is not None and curr_code_snapshot == prev_code_snapshot
        )
        same_as_wm_off = False
        docker_reference_snapshot = prev_code_snapshot
        if wmS == Decimal("0") and zero_strength_requested:
            if zero_strength_reference is None:
                raise RuntimeError("zero-strength comparison has no WM-OFF reference")
            zero_strength_comparison = compare_zero_strength_reference(
                contract=zero_strength_contract,
                reference=zero_strength_reference,
                candidate_snapshot=curr_code_snapshot,
                candidate_snapshot_hash=source_snapshot_hash,
                candidate_manifest=list(
                    diversity_record.get("generation_response_manifest") or []
                ),
            )
            same_as_wm_off = bool(
                zero_strength_comparison["source_exact_match"]
            )
            diversity_record["zero_strength_comparison"] = zero_strength_comparison
            zero_strength_audit.update(
                {
                    "comparison_status": zero_strength_comparison["status"],
                    "source_exact_match": same_as_wm_off,
                    "generated_text_exact_match": zero_strength_comparison[
                        "generated_text_exact_match"
                    ],
                    "finish_reasons_exact_match": zero_strength_comparison[
                        "finish_reasons_exact_match"
                    ],
                    "contract_status": zero_strength_comparison["contract_status"],
                }
            )
            reference_snapshot = zero_strength_reference["source_snapshot"]
            docker_reference_snapshot = reference_snapshot
            if same_as_wm_off:
                print(
                    f"[INFO] wmS=0 source exactly matches WM-OFF; "
                    f"reusing the validated baseline test"
                )
            else:
                level = "ERROR" if zero_strength_contract == "exact_noop" else "WARN"
                print(
                    f"[{level}] wmS=0 differs from WM-OFF: "
                    f"{zero_strength_comparison['source_diff']}; "
                    f"running the normal Docker and AI evaluation"
                )

        diversity_record.update(
            {
                "complete_source_snapshot": dict(curr_code_snapshot),
                "source_snapshot_hash": source_snapshot_hash,
                "same_as_previous_snapshot": same_as_previous,
                "same_as_wm_off_snapshot": same_as_wm_off,
                "already_seen_snapshot": source_snapshot_hash in seen_snapshot_hashes,
                "build_skipped_due_to_unchanged_snapshot": (
                    same_as_previous or same_as_wm_off
                ),
            }
        )
        batch_diversity_records.append(dict(diversity_record))
        _append_diversity_record(diversity_record)
        seen_snapshot_hashes.add(source_snapshot_hash)

        # 6) Preserve the existing previous-snapshot skip and Docker/build behavior.
        curr_code_snapshot, retCode, skipped = docker_exec(
            docker_reference_snapshot,
            codeFilePath,
            testFilePath,
            LANG,
            f"wmS={wmS}",
            prepared_code_snapshot=curr_code_snapshot,
        )

        # 7) Save the actual code that was compared/tested, after remove_leading_h2_line(...)
        shellPaste([codeFilePath], destPath)

        if skipped:
            # Source files are byte-for-byte identical to the previous wmS after cleanup.
            # Do not run docker, do not reuse/copy previous DTResults, and do not update result counts.
            print(f"[INFO] wmS={wmS} skipped docker test because source snapshot is unchanged.")
            batch_skipped_count += 1
            last_status = "same_as_wm_off" if same_as_wm_off else "skipped"

        else:
            batch_tested_count += 1
            DTResPath = (codeFilePath / "DTResults").resolve()
            if DTResPath.exists():
                try:
                    pat = re.compile(r"evaluation\.log")
                    logPath = find_path(DTResPath, pat, kind="file", recursive=True)
                    if logPath is None:
                        pat = re.compile(r"host_wrapper_\d{8}_\d{6}\.log")
                        logPath = find_path(DTResPath, pat, kind="file", recursive=True)
                    if logPath is not None:
                        last_log_path = str(logPath)
                        print(f"[INFO] Using log file for classification: {logPath}")
                        logContent = read_file(logPath)
                        logContent += filterPrompt
                        res = common_chat(client, Model.gpt4o_240513, [logContent], StreamMode=True)
                        last_classifier_output = str(res).strip()
                        label = _norm_label(res)
                        if label is not None:
                            batch_res_counts[label] += 1
                            last_label = label
                            last_status = label
                        else:
                            batch_res_counts[TEST_RESULT_UNCLASSIFIED_LABEL] += 1
                            last_status = "unclassified"
                            print(f"[WARN] Unrecognized result label from model: {res!r}", file=sys.stderr)
                    else:
                        batch_res_counts[TEST_RESULT_UNCLASSIFIED_LABEL] += 1
                        last_status = "unclassified:no_log"
                        print(f"[WARN] No usable log file found under {DTResPath}", file=sys.stderr)

                except Exception as e:
                    batch_res_counts[TEST_RESULT_UNCLASSIFIED_LABEL] += 1
                    last_status = "unclassified:error"
                    print(f"[ERROR] Failed to filter DTResults: {e}")

                shellPaste([DTResPath], destPath)
            else:
                batch_res_counts[TEST_RESULT_UNCLASSIFIED_LABEL] += 1
                last_status = "unclassified:no_dtresults"
                print(f"[WARN] {DTResPath} does not exist; skipping collection.", file=sys.stderr)

        if curr_code_snapshot:
            prev_code_snapshot = curr_code_snapshot

        try:
            ret_code_value = int(retCode)
        except (TypeError, ValueError):
            ret_code_value = retCode
        wmS_result = {
            **diversity_record,
            "wmS": str(wmS),
            "processor": processor_type,
            "rng_seed": iteration_rng_seed,
            "tested": not bool(skipped),
            "skipped": bool(skipped),
            "ret_code": ret_code_value,
            "result_label": last_label,
            "status": last_status,
            "classification_log": last_log_path,
            "classifier_output": last_classifier_output,
            "result_path": str(destPath),
        }
        batch_wms_results.append(wmS_result)
        try:
            _append_batch_progress(wmS_result)
            _write_batch_summary()
        except Exception as e:
            print(f"[WARN] Failed to update batch progress files for wmS={wmS}: {e}")
        _print_batch_test_stats(wmS, last_status)
        print(f"wmS={wmS} results have been saved to {destPath}")

    # Summary
    try:
        _write_batch_summary()
        print(f"[INFO] Batch summary saved to {summary_path}")
        print(f"[INFO] Batch progress JSONL saved to {progress_path}")
    except Exception as e:
        print(f"[WARN] Failed to write batch summary: {e}")
