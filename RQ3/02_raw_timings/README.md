# Raw timing records

- `logits_bias_raw.json` contains excluded warm-ups, 60 measured watermarked
  generations, 60 one-to-one WM-OFF baselines, generated source, pair order,
  processor-level timing, detector output, environment, configurations, and
  run-level bootstrap summaries. It is the only authoritative logits campaign.
  Every method has five `baseline_then_watermark` and five
  `watermark_then_baseline` pairs.
- `codemark_csn_js_raw.json` and `srcmarker_csn_js_raw.json` contain the 20
  excluded warm-ups and all 3,150 measured CodeSearchNet JavaScript samples
  for each method. Every row retains input/output hashes, selected
  transformations, true/predicted bits, raw seconds, and reference-token
  counts.
- `raw_timings.csv` is generated from those JSON records by
  `../05_analysis/reproduce_table_x.py`. Its `embedding_*` fields are the
  paired generation difference used by Table X; `processor_only_embedding_*`
  fields retain the attribution diagnostic. The JSON files are authoritative.

Warm-up rows are retained for auditability and excluded from all reported
statistics.
