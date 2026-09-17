# Release-language audit

The reviewer-facing first-party instructions, entry points, configurations,
and report builders are English. Run:

```bash
python3 tools/check_release_language.py
```

The check deliberately excludes these immutable evidence classes:

- raw RQ1/RQ2 observations and execution logs;
- Stage-0 prompts, model responses, generated architecture documents, and
  generated initial repositories;
- the frozen MetaGPT tree under `RQ1/source/reproduct/framework/metagpt/` and
  its experiment-time patched copy under `RQ1/source/DT/codeGen/MetaGPT/`;
- frozen watermark implementation/model-runtime snapshots under
  `RQ1/source/**/modelDeploy/`;
- the frozen SrcMarker checkout under
  `RQ2/source/training/SrcMarker_fresh/`.

Those files are provenance-bearing inputs or third-party/upstream snapshots.
Some contain Chinese comments, strings, or original sample text. Translating
them would alter the exact experiment input/source identity and could change
runtime prompts, exception strings, or parsing behavior. They are therefore
retained byte-faithfully and checksummed instead of silently rewritten.

First-party comments, reviewer documentation, configuration annotations, and
report labels outside those immutable scopes were normalized to English. The
only experiment fixture touched in executable RQ1 campaign code was rewritten
as an equivalent Unicode escape, preserving its runtime value. No raw result,
prediction, checkpoint, prompt response, or statistical value was translated.

Exact local source-normalization details and pre/post hashes are recorded in
`patches/LANGUAGE_NORMALIZATION.md`.
