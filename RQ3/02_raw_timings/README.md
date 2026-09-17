# Raw timing records

- `logits_bias_raw.json` contains the excluded warm-ups, 60 measured
  generations, generated source, processor-level timing, detector output,
  environment, configurations, and run-level bootstrap summaries.
- `codemark_csn_js_raw.json` and `srcmarker_csn_js_raw.json` contain the 20
  excluded warm-ups and all 3,150 measured CodeSearchNet JavaScript samples
  for each method. Every row retains input/output hashes, selected
  transformations, true/predicted bits, raw seconds, and reference-token
  counts.
- `raw_timings.csv` is generated from those JSON records by
  `../05_analysis/reproduce_table_x.py`; the JSON files are authoritative.

Warm-up rows are retained for auditability and excluded from all reported
statistics.
