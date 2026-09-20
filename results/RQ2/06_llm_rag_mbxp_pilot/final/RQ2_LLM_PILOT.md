# RQ2 LLM+RAG MBXP validation

The final execution-preservation cohort contains 45 baseline-qualified MBXP
programs: 15 C++, 15 Java, and 15 JavaScript.

| Language | Changed | Syntax-valid changed | Post-pass | EPR |
|---|---:|---:|---:|---:|
| C++ | 15 | 15 | 15 | 100% |
| Java | 15 | 15 | 15 | 100% |
| JavaScript | 15 | 15 | 15 | 100% |
| **Total** | **45** | **45** | **45** | **100%** |

Per-sample sources, tests, prompts, retrieved rules, transformed programs, and
execution outcomes are in `../epr/`. Execution logs are in
`../execution_logs/`, and the machine-readable final summary is
`rq2_llm_pilot.json`.
