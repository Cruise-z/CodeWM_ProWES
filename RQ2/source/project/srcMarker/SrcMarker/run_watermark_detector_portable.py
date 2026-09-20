#!/usr/bin/env python3
"""Portable CPU/CUDA SrcMarker extractor for an attacked JSONL file.

This entry point loads only the trained extractor encoder and watermark decoder
while preserving the experiment's tokenization and 512-token truncation
protocol.
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import sys
from pathlib import Path


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, nargs="+", help="One or more attacked JSONL files")
    ap.add_argument("--output", required=True, nargs="+", help="One output JSONL per input")
    ap.add_argument("--srcmarker-root", required=True)
    ap.add_argument("--checkpoint-path", required=True)
    ap.add_argument("--lang", choices=["java", "cpp", "javascript"], required=True)
    ap.add_argument("--source-field", default="after_obfus")
    ap.add_argument("--n-bits", type=int, default=4)
    ap.add_argument("--model-arch", choices=["gru", "transformer"], default="gru")
    ap.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    ap.add_argument("--batch-size", type=int, default=8)
    return ap.parse_args()


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    a = parse_args()
    if len(a.input) != len(a.output):
        raise ValueError("--input and --output must contain the same number of paths")
    input_paths = [str(Path(path).resolve()) for path in a.input]
    output_paths = [str(Path(path).resolve()) for path in a.output]
    root = Path(a.srcmarker_root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"SrcMarker root not found: {root}")
    sys.path.insert(0, str(root))

    import torch
    from torch.nn.utils.rnn import pad_sequence
    from code_tokenizer import CodeTokenizer
    from models import GRUEncoder, TransformerEncoderExtractor, MLP2

    if a.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(a.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available")

    checkpoint = torch.load(a.checkpoint_path, map_location="cpu", weights_only=False)
    vocab = checkpoint["vocab"]
    feature_dim = 768
    if a.model_arch == "gru":
        encoder = GRUEncoder(vocab_size=len(vocab), hidden_size=feature_dim, embedding_size=feature_dim)
    else:
        encoder = TransformerEncoderExtractor(
            vocab_size=len(vocab), embedding_size=feature_dim, hidden_size=feature_dim
        )
    decoder = MLP2(output_dim=a.n_bits, bn=False, input_dim=feature_dim)
    encoder.load_state_dict(checkpoint["model"])
    decoder.load_state_dict(checkpoint["wm_decoder"])
    del checkpoint
    gc.collect()
    encoder.to(device).eval()
    decoder.to(device).eval()

    old_cwd = Path.cwd()
    try:
        os.chdir(root)
        tokenizer = CodeTokenizer(lang=a.lang)
        row_groups = [read_jsonl(path) for path in input_paths]
        eligible = []
        for group_idx, rows in enumerate(row_groups):
            for row_idx, row in enumerate(rows):
                source = row.get(a.source_field)
                meta = row.get("attack_meta", {})
                syntax_valid = meta.get("syntax_valid", True)
                if meta.get("changed") is False or meta.get("status") == "no_op":
                    row["detector_status"] = "skipped_no_op"
                    continue
                if not isinstance(source, str) or not source or not syntax_valid:
                    row["detector_status"] = "skipped_invalid_attack"
                    continue
                try:
                    _, words = tokenizer.get_tokens(source)
                    ids = vocab.convert_tokens_to_ids(words)[:512]
                    if not ids:
                        raise ValueError("tokenizer returned no tokens")
                    eligible.append((group_idx, row_idx, ids))
                except Exception as exc:
                    row["detector_status"] = "tokenization_error"
                    row["detector_error"] = f"{type(exc).__name__}: {exc}"

        with torch.inference_mode():
            for start in range(0, len(eligible), a.batch_size):
                batch = eligible[start:start + a.batch_size]
                tensors = [torch.tensor(ids, dtype=torch.long) for _, _, ids in batch]
                lengths = torch.tensor([len(ids) for _, _, ids in batch], dtype=torch.long)
                x = pad_sequence(tensors, batch_first=True, padding_value=0).to(device)
                mask = (x == 0).to(device)
                features = encoder(x, lengths, mask)
                predictions = (torch.sigmoid(decoder(features)) > 0.5).long().cpu().tolist()
                for (group_idx, row_idx, _), pred in zip(batch, predictions):
                    row_groups[group_idx][row_idx]["obfus_extract"] = pred
                    row_groups[group_idx][row_idx]["detector_status"] = "ok"
    finally:
        os.chdir(old_cwd)

    for path, rows in zip(output_paths, row_groups):
        write_jsonl(path, rows)
    all_rows = [row for rows in row_groups for row in rows]
    counts = {status: sum(r.get("detector_status") == status for r in all_rows)
              for status in ["ok", "skipped_no_op", "skipped_invalid_attack", "tokenization_error"]}
    print(json.dumps({"files": len(row_groups), "rows": len(all_rows), "device": str(device),
                      "status_counts": counts}, indent=2))


if __name__ == "__main__":
    main()
