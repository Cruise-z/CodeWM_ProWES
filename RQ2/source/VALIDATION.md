# RQ2 final validation

The released source and evidence passed the following final checks:

- Python compilation completed for the first-party RQ2 source.
- All 16 RQ2 unit tests passed.
- Java 21, g++ 14/C++17, and Node 22 transformation checks passed.
- Eight independent fresh models completed 25 epochs with seed 42.
- All eight clean-generation outputs and all 32 rule-robustness cells completed.
- Each reported robustness cell uses 10,000 paired bootstrap replicates.
- The rule-based MBXP matrix contains 9,572 changed and syntax-valid programs
  and 9,444 post-transformation passes.
- The formal LLM+RAG run contains 1,000 responses: 972 valid attacks, 23
  no-ops, five syntax-invalid outputs, and no provider errors.
- All 972 valid LLM attacks received watermark predictions.
- The independent LLM+RAG MBXP pilot passes 45/45 programs.
- `python tools/verify_rq2_evidence.py` validates the released checkpoints,
  predictions, transformations, execution records, and aggregate statistics.

Only the final experiment source, formal observations, and final paper outputs
are retained in this Artifact.
