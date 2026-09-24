# Raw timing records

- `logits_bias_raw.json` is the sole authoritative v2 logits campaign. It holds
  180 measured watermarked generations and 180 adjacent WM-OFF baselines (30
  pairs per method), six formal RQ1 prompts, the randomized schedule, generated
  text, zero-observation processor metrics, standalone detector outputs, raw
  seconds, token counts, configuration, and environment. Every method has 15
  pairs in each order.
- `codemark_csn_js_raw.json` and `srcmarker_csn_js_raw.json` contain the 20
  excluded warm-ups and all 3,150 measured CodeSearchNet JavaScript samples
  per method. Every row retains source hashes, transformations, bits, raw
  seconds, reference tokens, internal model tokens, and truncation flags.
- `raw_timings.csv` is generated from those JSON records by
  `../05_analysis/reproduce_table_x.py`; JSON remains authoritative.

Warm-up rows are retained for auditability and excluded from all reported
statistics.
