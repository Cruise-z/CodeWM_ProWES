#!/usr/bin/env python3
"""Measure RQ3 embedding and extraction latency for SrcMarker or CodeMark.

The implementation reuses the fresh RQ2 checkpoint, dataset processor, runtime
transform manager, and method configuration. It intentionally omits CodeBLEU
and verbose sample logging so timing records are not perturbed by reporting.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from importlib.metadata import version as package_version
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import statistics
import subprocess
import time
from typing import Any

import torch
import tree_sitter
from torch.utils.data import DataLoader
from transformers import AutoTokenizer

from code_transform_provider import CodeTransformProvider
from data_processing import (
    CodeVocab,
    DataInstance,
    DynamicWMCollator,
    JsonlWMDatasetProcessor,
)
from experiment_config import build_code_transformers, validate_dataset_language
from models import (
    ConcatApproximator,
    ExtractGRUEncoder,
    GRUEncoder,
    MLP2,
    TransformSelector,
    TransformerEncoderExtractor,
    WMLinearEncoder,
)
from runtime_data_manager import InMemoryJitRuntimeDataManager


DATASET_LANG = {
    "github_c_funcs": "cpp",
    "github_java_funcs": "java",
    "csn_java": "java",
    "csn_js": "javascript",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def synchronize(device: torch.device) -> None:
    if device.type == "cuda":
        torch.cuda.synchronize(device)


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def ratio(rows: list[dict[str, Any]], seconds_field: str, tokens_field: str) -> float:
    return (
        sum(float(row[seconds_field]) for row in rows)
        * 1_000_000.0
        / sum(int(row[tokens_field]) for row in rows)
    )


def summarize(rows: list[dict[str, Any]], bootstrap: int, seed: int) -> dict[str, Any]:
    embedding = [float(row["embedding_ms_per_1k_tokens"]) for row in rows]
    extraction = [float(row["extraction_ms_per_1k_tokens"]) for row in rows]
    rng = random.Random(seed)
    embed_bootstrap = []
    extract_bootstrap = []
    for _ in range(bootstrap):
        sample = [rows[rng.randrange(len(rows))] for _ in rows]
        embed_bootstrap.append(ratio(sample, "embedding_seconds", "input_tokens"))
        extract_bootstrap.append(ratio(sample, "extraction_seconds", "watermarked_tokens"))
    return {
        "runs": len(rows),
        "input_tokens": sum(int(row["input_tokens"]) for row in rows),
        "watermarked_tokens": sum(int(row["watermarked_tokens"]) for row in rows),
        "input_model_tokens": sum(int(row["input_model_tokens"]) for row in rows),
        "watermarked_model_tokens": sum(
            int(row["watermarked_model_tokens"]) for row in rows
        ),
        "input_truncated_runs": sum(bool(row["input_truncated"]) for row in rows),
        "watermarked_truncated_runs": sum(bool(row["watermarked_truncated"]) for row in rows),
        "embedding_seconds": sum(float(row["embedding_seconds"]) for row in rows),
        "extraction_seconds": sum(float(row["extraction_seconds"]) for row in rows),
        "embedding_ms_per_1k_tokens": ratio(rows, "embedding_seconds", "input_tokens"),
        "embedding_median_ms_per_1k_tokens": statistics.median(embedding),
        "embedding_sd_ms_per_1k_tokens": statistics.stdev(embedding) if len(embedding) > 1 else 0.0,
        "embedding_95ci_ms_per_1k_tokens": [
            percentile(embed_bootstrap, 0.025),
            percentile(embed_bootstrap, 0.975),
        ],
        "extraction_ms_per_1k_tokens": ratio(rows, "extraction_seconds", "watermarked_tokens"),
        "extraction_median_ms_per_1k_tokens": statistics.median(extraction),
        "extraction_sd_ms_per_1k_tokens": statistics.stdev(extraction) if len(extraction) > 1 else 0.0,
        "extraction_95ci_ms_per_1k_tokens": [
            percentile(extract_bootstrap, 0.025),
            percentile(extract_bootstrap, 0.975),
        ],
    }


def command_output(command: list[str]) -> str | None:
    try:
        return subprocess.run(command, check=True, text=True, capture_output=True).stdout.strip()
    except Exception:
        return None


def build_models(
    checkpoint: dict[str, Any],
    vocab: CodeVocab,
    transform_capacity: int,
    vocab_mask: Any,
    args: argparse.Namespace,
    device: torch.device,
) -> dict[str, Any]:
    feature_dim = 768
    if args.model_arch == "gru":
        encoder = GRUEncoder(
            vocab_size=len(vocab), hidden_size=feature_dim, embedding_size=feature_dim
        )
    else:
        encoder = TransformerEncoderExtractor(
            vocab_size=len(vocab), embedding_size=feature_dim, hidden_size=feature_dim
        )
    selector = TransformSelector(
        vocab_size=len(vocab),
        transform_capacity=transform_capacity,
        input_dim=feature_dim,
        vocab_mask=vocab_mask,
        random_mask_prob=args.varmask_prob,
    )
    approximator = ConcatApproximator(
        vocab_size=len(vocab),
        transform_capacity=transform_capacity,
        input_dim=feature_dim,
        output_dim=feature_dim,
    )
    wm_encoder = WMLinearEncoder(args.n_bits, embedding_dim=feature_dim)
    wm_decoder = MLP2(output_dim=args.n_bits, bn=False, input_dim=feature_dim)
    extract_encoder: ExtractGRUEncoder | None = None

    encoder.load_state_dict(checkpoint["model"])
    if extract_encoder is not None:
        extract_encoder.load_state_dict(checkpoint["extract_encoder"])
    wm_encoder.load_state_dict(checkpoint["wm_encoder"])
    wm_decoder.load_state_dict(checkpoint["wm_decoder"])
    selector.load_state_dict(checkpoint["selector"])
    approximator.load_state_dict(checkpoint["approximator"])
    models = {
        "encoder": encoder,
        "selector": selector,
        "approximator": approximator,
        "wm_encoder": wm_encoder,
        "wm_decoder": wm_decoder,
        "extract_encoder": extract_encoder,
    }
    for model in models.values():
        if model is not None:
            model.to(device)
            model.eval()
    return models


def materialize_from_source(
    template: DataInstance,
    transform_manager: InMemoryJitRuntimeDataManager,
) -> DataInstance:
    """Re-tokenize raw source instead of reusing dataset-build token objects."""

    source_tokens, tokens = transform_manager.code_tokenizer.get_tokens(template.source)
    return DataInstance(
        template.id,
        template.source,
        source_tokens,
        tokens,
        task_label=template.task_label,
        transform_keys=template.transform_keys,
    )


def measure_batch(
    batch: Any,
    *,
    repeat: int,
    method: str,
    dataset: str,
    transform_capacity: int,
    transform_manager: InMemoryJitRuntimeDataManager,
    models: dict[str, Any],
    reference_tokenizer: Any,
    device: torch.device,
    random_mask: bool,
    var_transform_mode: str,
) -> dict[str, Any]:
    _, _, _, instance_ids, wms, wmids = batch

    synchronize(device)
    embed_start = time.perf_counter()
    original_templates = transform_manager.get_original_instances(instance_ids)
    original_instances = [
        materialize_from_source(instance, transform_manager)
        for instance in original_templates
    ]
    x, lengths, src_mask = transform_manager.load_to_tensor(original_instances)
    x = x.to(device)
    wms = wms.float().to(device)
    src_mask = src_mask.to(device)
    feasible = transform_manager.get_feasible_transform_ids(instance_ids)
    style_masks = []
    for item in feasible:
        mask = torch.ones(transform_capacity, device=device).bool()
        mask[item] = False
        style_masks.append(mask)
    style_masks_tensor = torch.stack(style_masks, dim=0)
    code_feature = models["encoder"](x, lengths, src_mask)
    wm_feature = models["wm_encoder"](wms)
    variable_output = models["selector"].var_selector_forward(
        code_feature, wm_feature, random_mask=random_mask
    )
    variable_ids = torch.argmax(variable_output, dim=1).tolist()
    style_output = models["selector"].transform_selector_forward(
        code_feature, wm_feature, transform_mask=style_masks_tensor
    )
    style_ids = torch.argmax(style_output, dim=1).tolist()
    transformed_instances, updates = transform_manager.varname_transform_on_instances(
        original_instances, variable_ids, mode=var_transform_mode
    )
    transformed_instances = transform_manager.transform_on_instances(
        transformed_instances, style_ids
    )
    synchronize(device)
    embedding_seconds = time.perf_counter() - embed_start

    synchronize(device)
    extraction_start = time.perf_counter()
    detector_instances = [
        materialize_from_source(instance, transform_manager)
        for instance in transformed_instances
    ]
    decoded_x, decoded_lengths, decoded_mask = transform_manager.load_to_tensor(
        detector_instances
    )
    decoded_x = decoded_x.to(device)
    decoded_mask = decoded_mask.to(device)
    if models["extract_encoder"] is not None:
        features = models["extract_encoder"](decoded_x, decoded_lengths, decoded_mask)
    else:
        features = models["encoder"](decoded_x, decoded_lengths, decoded_mask)
    outputs = models["wm_decoder"](features)
    probabilities = torch.sigmoid(outputs)
    predictions = (probabilities > 0.5).long()
    synchronize(device)
    extraction_seconds = time.perf_counter() - extraction_start

    original_source = original_instances[0].source
    watermarked_source = transformed_instances[0].source
    input_tokens = len(reference_tokenizer.encode(original_source, add_special_tokens=False))
    watermarked_tokens = len(
        reference_tokenizer.encode(watermarked_source, add_special_tokens=False)
    )
    if input_tokens <= 0 or watermarked_tokens <= 0:
        raise RuntimeError(f"empty reference-token sequence for {instance_ids[0]}")
    input_internal_tokens = len(original_instances[0].tokens)
    watermarked_internal_tokens = len(detector_instances[0].tokens)
    input_model_tokens = int(lengths[0])
    watermarked_model_tokens = int(decoded_lengths[0])
    return {
        "method": method,
        "dataset": dataset,
        "sample_uid": str(instance_ids[0]),
        "repeat": repeat,
        "rng_watermark_id": int(wmids[0].detach().cpu().item()),
        "true_bits": [int(value) for value in wms[0].detach().cpu().tolist()],
        "predicted_bits": [int(value) for value in predictions[0].detach().cpu().tolist()],
        "variable_transform_id": int(variable_ids[0]),
        "style_transform_id": int(style_ids[0]),
        "variable_update": [str(value) for value in updates[0]],
        "changed": original_source != watermarked_source,
        "input_source_sha256": sha256_text(original_source),
        "watermarked_source_sha256": sha256_text(watermarked_source),
        "input_tokens": input_tokens,
        "watermarked_tokens": watermarked_tokens,
        "input_internal_tokens": input_internal_tokens,
        "watermarked_internal_tokens": watermarked_internal_tokens,
        "input_model_tokens": input_model_tokens,
        "watermarked_model_tokens": watermarked_model_tokens,
        "input_truncated": input_internal_tokens > input_model_tokens,
        "watermarked_truncated": watermarked_internal_tokens > watermarked_model_tokens,
        "embedding_seconds": embedding_seconds,
        "extraction_seconds": extraction_seconds,
        "embedding_ms_per_1k_tokens": embedding_seconds * 1_000_000.0 / input_tokens,
        "extraction_ms_per_1k_tokens": extraction_seconds * 1_000_000.0 / watermarked_tokens,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--method", choices=["srcmarker", "codemark"], required=True)
    parser.add_argument("--dataset", choices=sorted(DATASET_LANG), default="csn_js")
    parser.add_argument("--lang", choices=["cpp", "java", "javascript"], default="javascript")
    parser.add_argument("--dataset-dir", type=Path, default=Path("datasets/csn_js"))
    parser.add_argument("--checkpoint-path", type=Path, required=True)
    parser.add_argument("--parser-library", type=Path, default=Path("parser/languages.so"))
    parser.add_argument("--metadata-dir", type=Path, default=Path("datasets"))
    parser.add_argument("--reference-tokenizer", type=Path, required=True)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cuda")
    parser.add_argument("--preprocess-workers", type=int, default=8)
    parser.add_argument("--max-samples", type=int)
    parser.add_argument("--warmups", type=int, default=20)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--bootstrap", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-bits", type=int, default=4)
    parser.add_argument("--model-arch", choices=["gru", "transformer"], default="gru")
    parser.add_argument("--varmask-prob", type=float, default=0.5)
    parser.add_argument("--var-transform-mode", choices=["replace", "append"], default="replace")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.dataset != "csn_js":
        raise ValueError("Table X semantic-preserving timing uses the canonical csn_js workload")
    validate_dataset_language(args.dataset, args.lang)
    if args.repeats < 1 or args.warmups < 0 or args.bootstrap < 1:
        parser.error("repeats/bootstrap must be positive and warmups non-negative")

    args.dataset_dir = args.dataset_dir.resolve()
    args.checkpoint_path = args.checkpoint_path.resolve()
    args.parser_library = args.parser_library.resolve()
    args.metadata_dir = args.metadata_dir.resolve()
    args.reference_tokenizer = args.reference_tokenizer.resolve()

    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable")
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if device.type == "cuda":
        torch.cuda.manual_seed_all(args.seed)

    parser_language = tree_sitter.Language(str(args.parser_library), args.lang)
    parser_instance = tree_sitter.Parser()
    parser_instance.set_language(parser_language)
    code_transformers = build_code_transformers(args.method)
    transform_computer = CodeTransformProvider(args.lang, parser_instance, code_transformers)
    dataset_processor = JsonlWMDatasetProcessor(args.lang, workers=args.preprocess_workers)
    checkpoint = torch.load(args.checkpoint_path, map_location="cpu", weights_only=False)
    vocab: CodeVocab = checkpoint["vocab"]
    test_instances = dataset_processor.load_jsonl(str(args.dataset_dir), split="test")
    if args.max_samples is not None:
        test_instances = test_instances[: args.max_samples]
    test_dataset = dataset_processor.build_dataset(test_instances, vocab)
    loader = DataLoader(
        test_dataset,
        batch_size=1,
        shuffle=False,
        collate_fn=DynamicWMCollator(args.n_bits),
    )
    transform_manager = InMemoryJitRuntimeDataManager(
        transform_computer, test_instances, args.lang
    )
    transform_manager.register_vocab(vocab)
    if args.method == "srcmarker":
        transform_manager.load_transform_mask(
            str(args.metadata_dir / f"feasible_transform_{args.dataset}.json")
        )
    else:
        transform_manager.load_transform_mask_from_components(
            str(args.metadata_dir / f"transforms_per_file_{args.dataset}.json"),
            code_transformers,
        )
    transform_manager.load_varname_dict(
        str(args.metadata_dir / f"variable_names_{args.dataset}.json")
    )
    transform_capacity = transform_manager.get_transform_capacity()
    vocab_mask = vocab.get_valid_identifier_mask()
    models = build_models(
        checkpoint,
        vocab,
        transform_capacity,
        vocab_mask,
        args,
        device,
    )
    reference_tokenizer = AutoTokenizer.from_pretrained(
        args.reference_tokenizer, local_files_only=True
    )

    warmup_rows = []
    with torch.inference_mode():
        for index, batch in enumerate(loader):
            if index >= args.warmups:
                break
            warmup_rows.append(
                measure_batch(
                    batch,
                    repeat=-1,
                    method=args.method,
                    dataset=args.dataset,
                    transform_capacity=transform_capacity,
                    transform_manager=transform_manager,
                    models=models,
                    reference_tokenizer=reference_tokenizer,
                    device=device,
                    random_mask=True,
                    var_transform_mode=args.var_transform_mode,
                )
            )

    rows = []
    benchmark_start = time.perf_counter()
    with torch.inference_mode():
        for repeat in range(args.repeats):
            random.seed(args.seed)
            torch.manual_seed(args.seed)
            if device.type == "cuda":
                torch.cuda.manual_seed_all(args.seed)
            for index, batch in enumerate(loader):
                row = measure_batch(
                    batch,
                    repeat=repeat,
                    method=args.method,
                    dataset=args.dataset,
                    transform_capacity=transform_capacity,
                    transform_manager=transform_manager,
                    models=models,
                    reference_tokenizer=reference_tokenizer,
                    device=device,
                    random_mask=True,
                    var_transform_mode=args.var_transform_mode,
                )
                rows.append(row)
                if (index + 1) % 250 == 0:
                    print(
                        f"{args.method}: repeat {repeat + 1}/{args.repeats}, "
                        f"sample {index + 1}/{len(test_dataset)}",
                        flush=True,
                    )

    tokenizer_files = {}
    for name in ("tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt"):
        path = args.reference_tokenizer / name
        if path.is_file():
            tokenizer_files[name] = sha256_file(path)
    dataset_test_path = args.dataset_dir / "test.jsonl"
    transform_metadata_paths = {
        "feasible_transform": args.metadata_dir / f"feasible_transform_{args.dataset}.json",
        "transforms_per_file": args.metadata_dir / f"transforms_per_file_{args.dataset}.json",
        "variable_names": args.metadata_dir / f"variable_names_{args.dataset}.json",
    }
    result = {
        "schema_version": 2,
        "protocol_version": "unintrusive-v2",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "measurement_contract": {
            "embedding": "raw input source re-tokenization, vocabulary tensorization, host-to-device transfer, feasible-mask lookup, encoder/selector inference, and variable/style source transformation",
            "extraction": "raw watermarked source re-tokenization, vocabulary tensorization, host-to-device transfer, encoder, bit decoder, and threshold",
            "precomputed_state": "dataset split, candidate transformation metadata, variable dictionaries, model/checkpoint loading, and reference-tokenizer loading are setup costs outside online timing",
            "cuda_synchronization": "the selected physical GPU is synchronized only at each outer online boundary",
            "embedding_normalization": "elapsed_seconds * 1,000,000 / Qwen reference tokens in input source",
            "extraction_normalization": "elapsed_seconds * 1,000,000 / Qwen reference tokens in watermarked source",
            "aggregation": "sum elapsed seconds / sum corresponding reference tokens; 95% intervals use 10,000 sample-level bootstrap resamples",
            "canonical_dataset": "CodeSearchNet JavaScript test split",
            "model_input_cap": 512,
        },
        "configuration": {
            "method": args.method,
            "dataset": args.dataset,
            "language": args.lang,
            "checkpoint": str(args.checkpoint_path.resolve()),
            "checkpoint_sha256": sha256_file(args.checkpoint_path),
            "dataset_test": str(dataset_test_path.resolve()),
            "dataset_test_sha256": sha256_file(dataset_test_path),
            "parser_library": str(args.parser_library),
            "parser_library_sha256": sha256_file(args.parser_library),
            "seed": args.seed,
            "n_bits": args.n_bits,
            "model_arch": args.model_arch,
            "varmask_prob": args.varmask_prob,
            "var_transform_mode": args.var_transform_mode,
            "transform_capacity": transform_capacity,
            "warmups": args.warmups,
            "repeats": args.repeats,
            "measured_samples": len(rows),
            "bootstrap_replicates": args.bootstrap,
        },
        "transformation_metadata": {
            name: {
                "path": str(path.resolve()),
                "sha256": sha256_file(path),
            }
            for name, path in transform_metadata_paths.items()
        },
        "reference_tokenizer": {
            "identifier": "Qwen/Qwen3-Coder-30B-A3B-Instruct",
            "resolved_path": str(args.reference_tokenizer.resolve()),
            "class": reference_tokenizer.__class__.__name__,
            "length": len(reference_tokenizer),
            "vocab_size": reference_tokenizer.vocab_size,
            "files_sha256": tokenizer_files,
        },
        "environment": {
            "artifact_source_commit": command_output([
                "git",
                "-C",
                str(Path(__file__).resolve().parents[2]),
                "rev-parse",
                "HEAD",
            ]),

            "python": platform.python_version(),
            "platform": platform.platform(),
            "torch": torch.__version__,
            "cuda": torch.version.cuda,
            "tree_sitter": package_version("tree-sitter"),
            "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
            "gpu": torch.cuda.get_device_name(device) if device.type == "cuda" else None,
            "nvidia_smi": command_output([
                "nvidia-smi",
                "--query-gpu=index,name,uuid,driver_version,memory.total",
                "--format=csv,noheader",
            ]),
            "benchmark_wall_seconds": time.perf_counter() - benchmark_start,
        },
        "summary": summarize(rows, args.bootstrap, args.seed),
        "warmups": warmup_rows,
        "runs": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = result["summary"]
    print(
        f"{args.method}: embedding={summary['embedding_ms_per_1k_tokens']:.2f} "
        f"ms/1K, extraction={summary['extraction_ms_per_1k_tokens']:.2f} ms/1K, "
        f"runs={summary['runs']}"
    )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
