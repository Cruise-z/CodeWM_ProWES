# Timing harnesses

- `benchmark_logits_bias.py` implements the non-intrusive v2 protocol. It uses
  six exact RQ1 Stage-1 prompts from `workloads.json`, fixes each method at its
  RQ1 EEI midpoint, and records 30 adjacent WM-ON/WM-OFF pairs per method.
  Generation is fixed at 256 tokens, pair order is balanced 15/15, and method
  order is shuffled within every workload-repeat block.
- Measured generation disables per-token clocks, per-token CUDA synchronization,
  and detection-only caches. Only the outer generation boundaries synchronize
  all visible devices. `test_unintrusive_v2.py` checks request-local propagation
  and final-text detector-state reconstruction.
- Extraction uses `/v1/watermark/detect`, which constructs a fresh processor and
  times final-text tokenization plus the complete detector. It never reuses
  state gathered during generation. SWEET includes its independent causal-LM
  entropy forward, and zero-work detections are rejected.
- `benchmark_semantic.py` loads the fresh RQ2 checkpoint and canonical 3,150-row
  CodeSearchNet JavaScript test split. Its embedding timer begins with raw-source
  tokenization; its extraction timer independently begins with raw watermarked
  source. Both include tensorization and device transfer.

The released logits campaign binds the sharded model server and client to
physical GPUs 2 and 3:

```bash
CUDA_VISIBLE_DEVICES=2,3 RQ1/source/reproduct/run_model_server.sh
CUDA_VISIBLE_DEVICES=2,3 python RQ3/01_timing_harness/benchmark_logits_bias.py \
  --endpoint http://127.0.0.1:8000 --repeats 5 --warmups 1 \
  --max-tokens 256 --bootstrap 10000 \
  --output RQ3/02_raw_timings/logits_bias_raw.json
```

The two semantic campaigns use the released fresh-training implementation and
run independently on physical GPUs 2 and 3. `RQ2_INPUTS` is the prepared RQ2
working tree containing the archived CSN-JavaScript split and transformation
metadata; their exact SHA-256 identities are embedded in each raw result.

```bash
ARTIFACT_ROOT=/path/to/CodeWM_ProWES
RQ2_INPUTS=/path/to/prepared/SrcMarker
QWEN_TOKENIZER=/path/to/Qwen3-Coder-30B-A3B-Instruct

cd "$RQ2_INPUTS"
CUDA_VISIBLE_DEVICES=2 \
PYTHONPATH="$ARTIFACT_ROOT/RQ2/source/training/SrcMarker_fresh" \
python "$ARTIFACT_ROOT/RQ3/01_timing_harness/benchmark_semantic.py" \
  --method codemark --checkpoint-path \
  "$ARTIFACT_ROOT/results/RQ2/02_training/checkpoints/fresh_rq2_codemark_42_csn_js/models_best.pt" \
  --parser-library "$ARTIFACT_ROOT/RQ2/source/cStyleLang/parser/languages.so" \
  --reference-tokenizer "$QWEN_TOKENIZER" --warmups 20 --repeats 1 \
  --output "$ARTIFACT_ROOT/RQ3/02_raw_timings/codemark_csn_js_raw.json"

CUDA_VISIBLE_DEVICES=3 \
PYTHONPATH="$ARTIFACT_ROOT/RQ2/source/training/SrcMarker_fresh" \
python "$ARTIFACT_ROOT/RQ3/01_timing_harness/benchmark_semantic.py" \
  --method srcmarker --checkpoint-path \
  "$ARTIFACT_ROOT/results/RQ2/02_training/checkpoints/fresh_rq2_srcmarker_42_csn_js/models_best.pt" \
  --parser-library "$ARTIFACT_ROOT/RQ2/source/cStyleLang/parser/languages.so" \
  --reference-tokenizer "$QWEN_TOKENIZER" --warmups 20 --repeats 1 \
  --output "$ARTIFACT_ROOT/RQ3/02_raw_timings/srcmarker_csn_js_raw.json"
```

The released implementation is under `../../RQ1/source/` and `../../RQ2/source/`.
Warm-ups are retained in raw JSON and excluded from summaries. Every harness
fails closed on missing work, mismatched token accounting, intrusive observation,
or unbalanced pair order.

These scripts write raw evidence. Normalization and Table X generation are
implemented separately in `../05_analysis/reproduce_table_x.py`.
