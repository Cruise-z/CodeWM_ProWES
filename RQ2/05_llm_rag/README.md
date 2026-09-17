# LLM + deterministic rule RAG

Exact system/user prompts, the 12-card frozen rule base, BM25 retrieval, output
parser, provider adapter, and full runner are in `../source/rq2_revision/` and
`../source/run_llm_full_1000.py`. Formal observations are under
`../../results/RQ2/05_llm_rag/`, including the pre-request cohort, 1,000
per-request records, returned snapshot and usage, per-sample retrieved/applied
rules, validity status, attacked predictions, logs, and 10,000-bootstrap
metrics. Credentials are not archived.
