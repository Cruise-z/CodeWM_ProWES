# RQ2 tables and figures

All figures are generated only from CSV files in `tables/`:

```bash
PYTHONPATH=.deps python plot_rq2_results.py \
  --table-dir deliverables/03_tables_figures/tables \
  --output-dir deliverables/03_tables_figures/figures
```

Files:

- `rq2_clean.csv`: fresh-checkpoint clean accuracy and hashes.
- `rq2_rule_robustness.csv`: 32 method/dataset/channel rule-attack cells and 95% CIs.
- `rq2_rule_epr.csv`: complete executable validation over MBCPP/MBJP/MBJSP.
- `rq2_llm_generation.csv`: 1,000-generation status, usage, model snapshot, cost, and hashes.
- `rq2_llm_robustness.csv`: eight LLM watermark cells and 95% CIs.
- `rq2_llm_method_contrasts.csv`: paired between-method contrasts on common valid UIDs.
- `rq2_llm_rule_usage.csv`: retrieved and model-reported applied rule frequencies.
- `rq2_paper_main.csv` / `.tex`: compact main-paper table.
- `rq2_rule_epr.tex`: appendix-ready EPR table.

Generation script SHA-256: `c36c4752b50a400fbaa56edd27ecf361b095bfbdf370100241fc46552df23aa2`.
