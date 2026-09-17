from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
import sys
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

CODEGEN_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODEGEN_DIR))

import agentCodeGen
import batch_runner


class _AsyncStore:
    def __init__(self) -> None:
        self.saved: list[dict] = []

    async def save(self, **kwargs) -> None:
        self.saved.append(kwargs)


class _Action:
    def __init__(self, filename: str, finish_reason: str) -> None:
        self.i_context = {"filename": filename}
        self.context = None
        self.rc = None
        self.config = None
        self.repo = SimpleNamespace(srcs=_AsyncStore())
        self.last_completion_metadata = {
            "finish_reason": finish_reason,
            "usage": {"completion_tokens": 4096},
            "content_character_count": 1200,
        }
        self.run_count = 0

    def set_context(self, context) -> None:
        self.context = context

    def set_env(self, env) -> None:
        pass

    def set_llm(self, llm) -> None:
        self.llm = llm

    async def run(self):
        self.run_count += 1
        return SimpleNamespace(
            filename=self.i_context["filename"],
            design_doc=None,
            task_doc=None,
            code_plan_and_change_doc=None,
            code_doc=SimpleNamespace(content="print('partial')"),
        )


def test_manual_action_runner_stops_after_saved_truncated_file() -> None:
    docs = SimpleNamespace(system_design=_AsyncStore(), task=_AsyncStore())
    context = SimpleNamespace(
        repo=SimpleNamespace(docs=docs),
        git_repo=SimpleNamespace(workdir="/tmp/test-workdir"),
        config=SimpleNamespace(inc=False),
    )
    company = SimpleNamespace(context=context, env=None)
    engineer = SimpleNamespace(llm=object(), rc=None)
    first = _Action("first.py", "length")
    second = _Action("second.py", "stop")

    report = asyncio.run(
        agentCodeGen._run_actions_manually(
            company,
            engineer,
            [first, second],
            abort_on_truncation=True,
        )
    )

    assert report["request_succeeded"] is True
    assert report["generation_complete"] is False
    assert report["aborted_on_truncation"] is True
    assert report["completed_file_count"] == 1
    assert report["saved_file_count"] == 1
    assert report["truncated_files"] == ["first.py"]
    assert first.run_count == 1
    assert second.run_count == 0
    assert report["files"][0]["usage"] == {"completion_tokens": 4096}


def test_exact_seed_preflight_runs_true_wmoff_generation(monkeypatch, tmp_path: Path) -> None:
    generated: list[tuple[str, dict, bool]] = []
    docker_calls: list[tuple] = []

    async def fake_code_gen(project: str, xargs: dict, *, abort_on_truncation: bool):
        generated.append((project, xargs, abort_on_truncation))
        return {
            "request_succeeded": True,
            "generation_complete": True,
            "truncated_files": [],
        }

    def fake_docker_exec(*args):
        docker_calls.append(args)
        return {"sample.py": "a" * 64}, 0, False

    monkeypatch.setattr(batch_runner, "get_programming_language", lambda path: "python")
    monkeypatch.setattr(batch_runner, "shellDelete", lambda *args, **kwargs: None)
    monkeypatch.setattr(batch_runner, "shellPaste", lambda *args, **kwargs: None)
    monkeypatch.setattr(batch_runner, "codeGen", fake_code_gen)
    monkeypatch.setattr(batch_runner, "docker_exec", fake_docker_exec)

    result = asyncio.run(
        batch_runner.validateRngSeed(
            123,
            "sample_project",
            str(tmp_path / "src"),
            str(tmp_path / "workspace"),
            tmp_path / "test.sh",
            {"temperature": 0.7, "top_p": 0.9, "max_tokens": 4096},
        )
    )

    assert result["passed"] is True
    assert result["docker_return_code"] == 0
    assert result["source_snapshot"] == {"sample.py": "a" * 64}
    assert result["source_snapshot_hash"]
    assert generated == [
        (
            "sample_project",
            {
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 4096,
                "rng_seed": 123,
                "internal_processor_names": [],
                "external_processor_names": [],
                "external_processor_params": {},
                "watermark_detect": False,
            },
            True,
        )
    ]
    assert len(docker_calls) == 1
    assert docker_calls[0][-1] == "rngS=123-wmoff-preflight"


def test_exact_seed_preflight_does_not_test_incomplete_generation(
    monkeypatch, tmp_path: Path
) -> None:
    async def fake_code_gen(project: str, xargs: dict, *, abort_on_truncation: bool):
        return {
            "request_succeeded": True,
            "generation_complete": False,
            "truncated_files": ["partial.py"],
        }

    monkeypatch.setattr(batch_runner, "get_programming_language", lambda path: "python")
    monkeypatch.setattr(batch_runner, "shellDelete", lambda *args, **kwargs: None)
    monkeypatch.setattr(batch_runner, "shellPaste", lambda *args, **kwargs: None)
    monkeypatch.setattr(batch_runner, "codeGen", fake_code_gen)
    monkeypatch.setattr(
        batch_runner,
        "docker_exec",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("Docker must not run for incomplete generation")
        ),
    )

    result = asyncio.run(
        batch_runner.validateRngSeed(
            123,
            "sample_project",
            str(tmp_path / "src"),
            str(tmp_path / "workspace"),
            tmp_path / "test.sh",
            {"temperature": 0.7, "max_tokens": 4096},
        )
    )

    assert result["passed"] is False
    assert result["generation_complete"] is False
    assert result["docker_return_code"] is None


def test_random_seed_selection_reports_attempt_status(monkeypatch, capsys) -> None:
    seeds = iter((111, 222))

    async def fake_validate_rng_seed(seed: int, *args, **kwargs):
        if seed == 111:
            return {
                "passed": False,
                "generation_complete": False,
                "docker_return_code": None,
            }
        return {
            "passed": True,
            "generation_complete": True,
            "docker_return_code": 0,
        }

    monkeypatch.setattr(batch_runner, "make_seed", lambda bits: next(seeds))
    monkeypatch.setattr(batch_runner, "validateRngSeed", fake_validate_rng_seed)

    selected = asyncio.run(
        batch_runner.selectRngSeed(
            "sample_project",
            "/tmp/src",
            "/tmp/workspace",
            Path("/tmp/test.sh"),
            {"temperature": 0.7, "max_tokens": 4096},
        )
    )

    output = capsys.readouterr().out
    assert selected == 222
    assert "rng_seed not configured; starting random WM-OFF seed selection" in output
    assert "WM-OFF seed attempt 1 start: rng_seed=111" in output
    assert (
        "WM-OFF seed attempt 1 failed: rng_seed=111 "
        "generation_complete=False docker_return_code=None; retrying"
    ) in output
    assert "WM-OFF seed attempt 2 start: rng_seed=222" in output
    assert (
        "WM-OFF seed attempt 2 passed: rng_seed=222 "
        "generation_complete=True docker_return_code=0"
    ) in output


def test_batch_attempts_later_strength_after_consecutive_truncations(
    monkeypatch, tmp_path: Path
) -> None:
    project_name = "sample_project"
    src_path = tmp_path / "src"
    workspace_path = tmp_path / "workspace"
    results_path = tmp_path / "results"
    repo_path = src_path / project_name
    code_path = workspace_path / project_name / project_name
    repo_path.mkdir(parents=True)
    (src_path / "storage").mkdir()
    workspace_path.mkdir()

    calls: list[Decimal] = []
    docker_labels: list[str] = []

    async def fake_code_gen(project: str, xargs: dict, *, abort_on_truncation: bool):
        assert project == project_name
        assert abort_on_truncation is True
        strength = Decimal(
            str(xargs["external_processor_params"]["waterfall"]["kappa"])
        )
        calls.append(strength)
        code_path.mkdir(parents=True, exist_ok=True)
        filename = f"generated_{strength}.py"
        if strength == Decimal("3"):
            (code_path / filename).write_text("print('complete')\n", encoding="utf-8")
            return {
                "request_succeeded": True,
                "generation_complete": True,
                "aborted_on_truncation": False,
                "expected_file_count": 1,
                "completed_file_count": 1,
                "saved_file_count": 1,
                "files": [
                    {
                        "filename": filename,
                        "finish_reason": "stop",
                        "truncated": False,
                        "saved": True,
                    }
                ],
                "truncated_files": [],
            }

        (code_path / filename).write_text("print('partial')\n", encoding="utf-8")
        return {
            "request_succeeded": True,
            "generation_complete": False,
            "aborted_on_truncation": True,
            "expected_file_count": 3,
            "completed_file_count": 1,
            "saved_file_count": 1,
            "files": [
                {
                    "filename": filename,
                    "finish_reason": "length",
                    "usage": {"completion_tokens": 4096},
                    "truncated": True,
                    "saved": True,
                }
            ],
            "truncated_files": [filename],
        }

    def fake_shell_delete(path, dry_run=False) -> None:
        target = Path(path)
        for child in target.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()

    def fake_shell_paste(sources, target) -> None:
        target_path = Path(target)
        target_path.mkdir(parents=True, exist_ok=True)
        if target_path == workspace_path:
            code_path.mkdir(parents=True, exist_ok=True)
            return
        for source in map(Path, sources):
            shutil.copytree(source, target_path / source.name, dirs_exist_ok=True)

    monkeypatch.setattr(batch_runner, "Client", lambda *args, **kwargs: object())
    monkeypatch.setattr(batch_runner, "get_programming_language", lambda path: "python")
    monkeypatch.setattr(batch_runner, "strength_values", lambda config: [Decimal("1"), Decimal("2"), Decimal("3")])
    monkeypatch.setattr(batch_runner, "build_result_dir", lambda *args, **kwargs: "guard-test")
    monkeypatch.setattr(batch_runner, "codeGen", fake_code_gen)
    monkeypatch.setattr(batch_runner, "shellDelete", fake_shell_delete)
    monkeypatch.setattr(batch_runner, "shellPaste", fake_shell_paste)
    def fake_docker_exec(previous_snapshot, *args, **kwargs):
        docker_labels.append(args[3])
        return kwargs["prepared_code_snapshot"], 0, False

    monkeypatch.setattr(batch_runner, "docker_exec", fake_docker_exec)

    args = {
        "temperature": 0.7,
        "max_tokens": 4096,
        "processor_names_ext": "waterfall",
        "id_mu": 42,
        "k_p": 1,
        "n_gram": 2,
        "wm_fn": "fourier",
        "auto_reset": True,
        "detect_mode": "batch",
    }
    asyncio.run(
        batch_runner.codeGenBatch(
            123,
            project_name,
            str(src_path),
            str(workspace_path),
            str(results_path),
            tmp_path / "unused-test-script.sh",
            args,
            {"values": ["1", "2", "3"]},
        )
    )

    assert calls == [Decimal("1"), Decimal("2"), Decimal("3")]
    assert docker_labels == ["wmS=3"]
    summary_path = results_path / "guard-test" / f"{project_name}_batch_summary_rngS=123.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["counts"]["[Generation Incomplete]"] == 2
    assert summary["counts"]["[Test Result Unclassified]"] == 1
    assert "generation_truncated_count" not in summary
    assert "unclassified_count" not in summary
    assert "test_result_unclassified_count" not in summary
    assert summary["configured_strength_count"] == 3
    assert summary["processed_strength_count"] == 3
    assert [result["status"] for result in summary["wmS_results"]] == [
        "generation_truncated",
        "generation_truncated",
        "unclassified:no_dtresults",
    ]
    assert [result["tested"] for result in summary["wmS_results"]] == [
        False,
        False,
        True,
    ]
    assert all(
        Path(result["generation_status_path"]).is_file()
        for result in summary["wmS_results"][:2]
    )


def _run_zero_strength_case(monkeypatch, tmp_path: Path, candidate_code: str) -> dict:
    project_name = "sample_project"
    src_path = tmp_path / "src"
    workspace_path = tmp_path / "workspace"
    results_path = tmp_path / "results"
    repo_path = src_path / project_name
    code_path = workspace_path / project_name / project_name
    repo_path.mkdir(parents=True)
    (src_path / "storage").mkdir()
    workspace_path.mkdir()

    baseline_code = "print('baseline')\n"
    filename = "generated.py"
    baseline_digest = hashlib.sha256(baseline_code.encode("utf-8")).hexdigest()
    candidate_digest = hashlib.sha256(candidate_code.encode("utf-8")).hexdigest()
    baseline_snapshot = {filename: baseline_digest}
    baseline_manifest = [
        {
            "filename": filename,
            "finish_reason": "stop",
            "response_content_sha256": "a" * 64,
            "generated_code_sha256": baseline_digest,
            "detection_payload_sha256": "b" * 64,
        }
    ]
    candidate_manifest = [
        {
            "filename": filename,
            "finish_reason": "stop",
            "response_content_sha256": "c" * 64,
            "generated_code_sha256": candidate_digest,
            "detection_payload_sha256": "d" * 64,
        }
    ]
    validate_calls: list[dict] = []
    docker_calls: list[tuple[dict[str, str], dict[str, str]]] = []

    async def fake_validate_rng_seed(
        rng_seed,
        project,
        src,
        workspace,
        test_file,
        args,
        lang=None,
    ):
        validate_calls.append(dict(args))
        code_path.mkdir(parents=True, exist_ok=True)
        (code_path / filename).write_text(baseline_code, encoding="utf-8")
        return {
            "rng_seed": rng_seed,
            "passed": True,
            "generation_complete": True,
            "docker_return_code": 0,
            "generation_report": {"generation_complete": True},
            "generation_response_manifest": baseline_manifest,
            "source_snapshot": baseline_snapshot,
            "source_snapshot_hash": batch_runner.hash_code_snapshot(baseline_snapshot),
        }

    async def fake_code_gen(project: str, xargs: dict, *, abort_on_truncation: bool):
        assert xargs["rng_seed"] == 123
        assert xargs["external_processor_params"]["waterfall"]["kappa"] == 0.0
        code_path.mkdir(parents=True, exist_ok=True)
        (code_path / filename).write_text(candidate_code, encoding="utf-8")
        return {
            "request_succeeded": True,
            "generation_complete": True,
            "aborted_on_truncation": False,
            "expected_file_count": 1,
            "completed_file_count": 1,
            "saved_file_count": 1,
            "files": candidate_manifest,
            "truncated_files": [],
        }

    def fake_shell_delete(path, dry_run=False) -> None:
        target = Path(path)
        target.mkdir(parents=True, exist_ok=True)
        for child in target.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()

    def fake_shell_paste(sources, target) -> None:
        target_path = Path(target)
        target_path.mkdir(parents=True, exist_ok=True)
        if target_path == workspace_path:
            code_path.mkdir(parents=True, exist_ok=True)
            return
        for source in map(Path, sources):
            shutil.copytree(source, target_path / source.name, dirs_exist_ok=True)

    def fake_docker_exec(previous_snapshot, *args, **kwargs):
        current_snapshot = kwargs["prepared_code_snapshot"]
        docker_calls.append((previous_snapshot, current_snapshot))
        skipped = previous_snapshot == current_snapshot
        if not skipped:
            dt_results = code_path / "DTResults"
            dt_results.mkdir(parents=True, exist_ok=True)
            (dt_results / "evaluation.log").write_text("all checks passed\n", encoding="utf-8")
        return current_snapshot, 0, skipped

    monkeypatch.setattr(batch_runner, "Client", lambda *args, **kwargs: object())
    monkeypatch.setattr(batch_runner, "get_programming_language", lambda path: "python")
    monkeypatch.setattr(batch_runner, "build_result_dir", lambda *args, **kwargs: "zero-test")
    monkeypatch.setattr(batch_runner, "validateRngSeed", fake_validate_rng_seed)
    monkeypatch.setattr(batch_runner, "codeGen", fake_code_gen)
    monkeypatch.setattr(batch_runner, "shellDelete", fake_shell_delete)
    monkeypatch.setattr(batch_runner, "shellPaste", fake_shell_paste)
    monkeypatch.setattr(batch_runner, "docker_exec", fake_docker_exec)
    monkeypatch.setattr(batch_runner, "common_chat", lambda *args, **kwargs: "[Pass]")

    args = {
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 4096,
        "processor_names_ext": "waterfall",
        "id_mu": 42,
        "k_p": 1,
        "n_gram": 2,
        "wm_fn": "fourier",
        "auto_reset": True,
        "detect_mode": "batch",
    }
    reference_cache: dict = {}
    asyncio.run(
        batch_runner.codeGenBatch(
            123,
            project_name,
            str(src_path),
            str(workspace_path),
            str(results_path),
            tmp_path / "unused-test-script.sh",
            args,
            {"values": ["0.0"]},
            wm_off_reference_cache=reference_cache,
        )
    )

    assert validate_calls == [args]
    assert len(reference_cache) == 1
    assert docker_calls == [(baseline_snapshot, {filename: candidate_digest})]
    summary_path = results_path / "zero-test" / f"{project_name}_batch_summary_rngS=123.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    reference_artifact_path = Path(
        summary["zero_strength_audit"]["reference_artifact_path"]
    )
    assert reference_artifact_path == (
        results_path
        / "zero-test"
        / "wm_off_reference_rngS=123"
        / project_name
    ).resolve()
    assert (reference_artifact_path / filename).read_text(encoding="utf-8") == baseline_code
    return summary


def test_zero_strength_exact_match_reuses_validated_wmoff(monkeypatch, tmp_path: Path) -> None:
    summary = _run_zero_strength_case(monkeypatch, tmp_path, "print('baseline')\n")

    assert summary["zero_strength_audit"]["contract"] == "exact_noop"
    assert summary["zero_strength_audit"]["contract_status"] == "satisfied"
    assert summary["zero_strength_audit"]["source_exact_match"] is True
    assert summary["tested_count"] == 0
    assert summary["skipped_count"] == 1
    assert summary["wmS_results"][0]["status"] == "same_as_wm_off"


def test_zero_strength_difference_is_recorded_and_tested(monkeypatch, tmp_path: Path) -> None:
    summary = _run_zero_strength_case(monkeypatch, tmp_path, "print('changed')\n")

    assert summary["zero_strength_audit"]["contract_status"] == "violated"
    assert summary["zero_strength_audit"]["source_exact_match"] is False
    assert summary["tested_count"] == 1
    assert summary["skipped_count"] == 0
    assert summary["counts"]["[Pass]"] == 1
    assert summary["wmS_results"][0]["status"] == "[Pass]"
