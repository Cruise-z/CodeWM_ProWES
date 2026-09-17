#!/usr/bin/env python3
"""Build the reviewer-facing RQ1 prompt bundle from immutable evidence.

Stage 0 copies the 42 exact architecture idea payloads. Stage 1 reconstructs
the 480 exact WriteCode user messages from the serialized Engineer todos and
the accepted baseline outputs. Every reconstructed pre-normalization source is
checked against the generated-code SHA-256 recorded during the accepted run.
"""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PROMPT_ROOT = ROOT / "RQ1" / "02_prompts"
ARCHITECTURES = ROOT / "RQ1" / "03_architecture_checkpoints"
BASELINE = ROOT / "results" / "RQ1" / "05_baseline_qualification"
TASK_MANIFEST = ROOT / "RQ1" / "01_task_specs" / "manifest.json"
WRITE_CODE_SOURCE = (
    ROOT
    / "RQ1"
    / "source"
    / "reproduct"
    / "framework"
    / "metagpt"
    / "actions"
    / "write_code.py"
)
ROLE_SOURCE = (
    ROOT
    / "RQ1"
    / "source"
    / "reproduct"
    / "framework"
    / "metagpt"
    / "roles"
    / "role.py"
)
ENGINEER_SOURCE = (
    ROOT
    / "RQ1"
    / "source"
    / "reproduct"
    / "framework"
    / "metagpt"
    / "roles"
    / "engineer.py"
)
def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write an empty inventory: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def literal_assignment(path: Path, name: str) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            value = ast.literal_eval(node.value)
            if not isinstance(value, str):
                raise TypeError(f"{name} in {path} is not a string")
            return value
    raise KeyError(f"{name} not found in {path}")


def class_string_assignment(path: Path, class_name: str, name: str) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        for item in node.body:
            target = None
            value_node = None
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                target, value_node = item.target.id, item.value
            elif isinstance(item, ast.Assign) and len(item.targets) == 1:
                if isinstance(item.targets[0], ast.Name):
                    target, value_node = item.targets[0].id, item.value
            if target == name and value_node is not None:
                value = ast.literal_eval(value_node)
                if not isinstance(value, str):
                    raise TypeError(f"{class_name}.{name} in {path} is not a string")
                return value
    raise KeyError(f"{class_name}.{name} not found in {path}")


def engineer_system_prompt() -> str:
    prefix_template = literal_assignment(ROLE_SOURCE, "PREFIX_TEMPLATE")
    constraint_template = literal_assignment(ROLE_SOURCE, "CONSTRAINT_TEMPLATE")
    values = {
        key: class_string_assignment(ENGINEER_SOURCE, "Engineer", key)
        for key in ("profile", "name", "goal", "constraints")
    }
    return prefix_template.format(
        profile=values["profile"], name=values["name"], goal=values["goal"]
    ) + constraint_template.format(constraints=values["constraints"])


def safe_filename(index: int, filename: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "__", filename).strip("_")
    return f"{index:03d}__{normalized}"


def engineer_todos(team: dict[str, Any]) -> list[dict[str, Any]]:
    roles = team.get("env", {}).get("roles", {})
    if isinstance(roles, str):
        roles = json.loads(roles)
    engineer = roles.get("Engineer") or roles.get("engineer")
    if not isinstance(engineer, dict):
        raise ValueError("serialized checkpoint has no Engineer role")
    todos = engineer.get("code_todos")
    if not isinstance(todos, list) or not todos:
        raise ValueError("serialized checkpoint has no Engineer.code_todos")
    return todos


def restore_raw_sources(
    accepted_repository: Path, generation_report: dict[str, Any]
) -> tuple[dict[str, str], dict[str, str]]:
    """Reverse the evaluator's optional leading-H2 cleanup, verified by hash."""
    sources: dict[str, str] = {}
    strategies: dict[str, str] = {}
    for record in generation_report["files"]:
        filename = record["filename"]
        normalized = (accepted_repository / filename).read_text(encoding="utf-8")
        candidate_pairs = [
            ("accepted_repository_content", normalized),
            ("restored_leading_h2", f"## {filename}\n{normalized}"),
            ("restored_compact_leading_h2", f"##{filename}\n{normalized}"),
            ("restored_code_label_leading_h2", f"## Code: {filename}\n{normalized}"),
            ("restored_basename_leading_h2", f"## {Path(filename).name}\n{normalized}"),
        ]
        candidates = {source: strategy for strategy, source in reversed(candidate_pairs)}
        matches = [
            (strategy, source)
            for source, strategy in candidates.items()
            if sha256_bytes(source.encode("utf-8"))
            == record["generated_code_sha256"]
        ]
        if len(matches) != 1:
            raise ValueError(
                f"cannot uniquely restore pre-normalization source for {filename}: "
                f"{len(matches)} matching candidates"
            )
        strategies[filename], sources[filename] = matches[0]
    return sources, strategies


def build() -> dict[str, Any]:
    manifest = read_json(TASK_MANIFEST)
    prompt_template = literal_assignment(WRITE_CODE_SOURCE, "PROMPT_TEMPLATE")
    system_prompt = engineer_system_prompt()
    languages = manifest["languages"]

    stage0_root = PROMPT_ROOT / "stage0"
    stage1_root = PROMPT_ROOT / "stage1"
    for generated in (stage0_root / "rendered", stage1_root / "rendered"):
        if generated.exists():
            shutil.rmtree(generated)
        generated.mkdir(parents=True)

    system_prompt_path = stage1_root / "system_prompt.txt"
    system_prompt_path.write_text(system_prompt, encoding="utf-8")

    stage0_rows: list[dict[str, Any]] = []
    stage1_rows: list[dict[str, Any]] = []
    restored_counts = {"accepted_repository_content": 0, "restored_leading_h2": 0}

    for project in manifest["projects"]:
        project_dir = f"p{int(project['project_id']):02d}_{project['slug']}"
        for language in languages:
            unit_id = f"{project_dir}_{language}"
            checkpoint = ARCHITECTURES / project_dir / language / "architecture"
            prompt_source = checkpoint / "prompt.txt"
            evidence_path = checkpoint / "evidence.json"
            team_path = checkpoint / "team" / "team.json"
            evidence = read_json(evidence_path)
            team = read_json(team_path)

            prompt_sha = sha256_file(prompt_source)
            if prompt_sha != evidence["prompt_sha256"]:
                raise ValueError(f"Stage-0 prompt hash mismatch for {unit_id}")
            if sha256_file(team_path) != evidence["team_json_sha256"]:
                raise ValueError(f"team checkpoint hash mismatch for {unit_id}")

            stage0_output = stage0_root / "rendered" / project_dir / language / "user_prompt.txt"
            stage0_output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(prompt_source, stage0_output)
            stage0_rows.append(
                {
                    "unit_id": unit_id,
                    "project_id": project["project_id"],
                    "project_slug": project["slug"],
                    "language": language,
                    "prompt_path": relative(stage0_output),
                    "prompt_sha256": prompt_sha,
                    "checkpoint_path": relative(team_path),
                    "checkpoint_sha256": evidence["team_json_sha256"],
                    "architecture_model": evidence["architecture_model"]["model"],
                    "architecture_base_url": evidence["architecture_model"]["base_url"],
                    "source_prompt_path": relative(prompt_source),
                }
            )

            accepted_evidence_path = (
                BASELINE / "units" / project_dir / language / "accepted" / "evidence.json"
            )
            accepted_evidence = read_json(accepted_evidence_path)
            report_path = BASELINE / accepted_evidence["attempt_generation_report"]
            report = read_json(report_path)
            accepted_repository = accepted_evidence_path.parent / "repository"
            raw_sources, restore_strategies = restore_raw_sources(
                accepted_repository, report
            )
            report_by_filename = {item["filename"]: item for item in report["files"]}

            todos = engineer_todos(team)
            todo_filenames = [
                json.loads(todo["i_context"]["content"])["filename"] for todo in todos
            ]
            report_filenames = [item["filename"] for item in report["files"]]
            if todo_filenames != report_filenames:
                raise ValueError(f"todo/report order mismatch for {unit_id}")

            generated: set[str] = set()
            for action_index, todo in enumerate(todos, 1):
                context = json.loads(todo["i_context"]["content"])
                filename = context["filename"]
                task = json.loads(context["task_doc"]["content"])
                task_list = task["Task list"]
                if task_list != todo_filenames:
                    raise ValueError(f"Task list mismatch in {unit_id}/{filename}")

                code_parts = []
                visible_sources = []
                for dependency in task_list:
                    if dependency == filename or dependency not in generated:
                        continue
                    source = raw_sources[dependency]
                    code_parts.append(f"----- {dependency}\n```{source}```")
                    visible_sources.append(
                        {
                            "filename": dependency,
                            "generated_code_sha256": sha256_bytes(source.encode("utf-8")),
                            "restoration": restore_strategies[dependency],
                        }
                    )
                code_context = "\n".join(code_parts)
                user_prompt = prompt_template.format(
                    design=context["design_doc"]["content"],
                    task=context["task_doc"]["content"],
                    code=code_context,
                    logs="",
                    feedback="",
                    filename=todo["i_context"]["filename"],
                    summary_log="",
                )

                action_stem = safe_filename(action_index, filename)
                action_dir = stage1_root / "rendered" / project_dir / language / action_stem
                action_dir.mkdir(parents=True, exist_ok=True)
                user_prompt_path = action_dir / "user_prompt.txt"
                context_path = action_dir / "input_context.json"
                request_path = action_dir / "request_metadata.json"
                user_prompt_path.write_text(user_prompt, encoding="utf-8")
                write_json(context_path, context)

                response = report_by_filename[filename]
                metadata = {
                    "schema_version": 1,
                    "status": "exact_reconstruction_from_immutable_run_state",
                    "unit_id": unit_id,
                    "action_index": action_index,
                    "filename": filename,
                    "system_prompt_path": relative(system_prompt_path),
                    "system_prompt_sha256": sha256_file(system_prompt_path),
                    "user_prompt_path": relative(user_prompt_path),
                    "user_prompt_sha256": sha256_file(user_prompt_path),
                    "input_context_path": relative(context_path),
                    "input_context_sha256": sha256_file(context_path),
                    "visible_prior_sources": visible_sources,
                    "empty_runtime_fields": ["debug_logs", "bug_feedback", "summary_log"],
                    "checkpoint_path": relative(team_path),
                    "checkpoint_sha256": evidence["team_json_sha256"],
                    "accepted_evidence_path": relative(accepted_evidence_path),
                    "accepted_generation_report_path": relative(report_path),
                    "rng_seed": accepted_evidence["rng_seed"],
                    "model": response.get("model"),
                    "response_id": response.get("response_id"),
                    "finish_reason": response.get("finish_reason"),
                    "usage": response.get("usage", {}),
                    "response_content_sha256": response.get("response_content_sha256"),
                    "generated_code_sha256": response["generated_code_sha256"],
                    "accepted_source_restoration": restore_strategies[filename],
                }
                write_json(request_path, metadata)
                restored_counts[restore_strategies[filename]] = (
                    restored_counts.get(restore_strategies[filename], 0) + 1
                )
                stage1_rows.append(
                    {
                        "unit_id": unit_id,
                        "project_id": project["project_id"],
                        "project_slug": project["slug"],
                        "language": language,
                        "action_index": action_index,
                        "filename": filename,
                        "system_prompt_sha256": metadata["system_prompt_sha256"],
                        "user_prompt_path": relative(user_prompt_path),
                        "user_prompt_sha256": metadata["user_prompt_sha256"],
                        "input_context_path": relative(context_path),
                        "input_context_sha256": metadata["input_context_sha256"],
                        "request_metadata_path": relative(request_path),
                        "checkpoint_sha256": evidence["team_json_sha256"],
                        "rng_seed": accepted_evidence["rng_seed"],
                        "model": response.get("model"),
                        "response_id": response.get("response_id"),
                        "generated_code_sha256": response["generated_code_sha256"],
                    }
                )
                generated.add(filename)

    if len(stage0_rows) != 42:
        raise ValueError(f"expected 42 Stage-0 prompts, found {len(stage0_rows)}")
    if len(stage1_rows) != 480:
        raise ValueError(f"expected 480 Stage-1 prompts, found {len(stage1_rows)}")

    write_csv(stage0_root / "prompt_manifest.csv", stage0_rows)
    write_json(stage0_root / "prompt_manifest.json", {"rows": stage0_rows})
    write_csv(stage1_root / "prompt_manifest.csv", stage1_rows)
    write_json(stage1_root / "prompt_manifest.json", {"rows": stage1_rows})
    summary = {
        "schema_version": 1,
        "stage0_prompt_count": len(stage0_rows),
        "stage0_counts_by_language": {
            language: sum(row["language"] == language for row in stage0_rows)
            for language in languages
        },
        "stage1_prompt_count": len(stage1_rows),
        "stage1_counts_by_language": {
            language: sum(row["language"] == language for row in stage1_rows)
            for language in languages
        },
        "stage1_source_restoration_counts": restored_counts,
        "write_code_source": relative(WRITE_CODE_SOURCE),
        "write_code_source_sha256": sha256_file(WRITE_CODE_SOURCE),
        "role_source": relative(ROLE_SOURCE),
        "role_source_sha256": sha256_file(ROLE_SOURCE),
        "engineer_source": relative(ENGINEER_SOURCE),
        "engineer_source_sha256": sha256_file(ENGINEER_SOURCE),
        "task_manifest": relative(TASK_MANIFEST),
        "task_manifest_sha256": sha256_file(TASK_MANIFEST),
    }
    write_json(PROMPT_ROOT / "bundle_summary.json", summary)
    return summary


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
