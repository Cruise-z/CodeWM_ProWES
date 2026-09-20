# Release-language audit

The reviewer-facing first-party instructions, entry points, configurations,
and report builders are English. Run:

```bash
python3 tools/check_release_language.py
```

The check deliberately excludes these immutable evidence classes:

- raw RQ1/RQ2 observations and execution logs, including the immutable RQ1
  baseline attempt/accepted/replay trees;
- Stage-0 prompts, generated architecture documents, generated initial
  repositories, and the Stage-1 rendered prompts/input contexts reconstructed
  byte-faithfully from those documents and accepted-run sources;
- the frozen MetaGPT tree under `RQ1/source/reproduct/framework/metagpt/` and
  its experiment-time patched copy under `RQ1/source/DT/codeGen/MetaGPT/`;
- frozen auxiliary RAG/sweet-watermark snapshots under
  `RQ1/source/DT/codeGen/modelDeploy/RAG/`.

Those files are provenance-bearing inputs or third-party/upstream snapshots.
Some contain Chinese comments, strings, or original sample text. Translating
them would alter the exact experiment input/source identity and could change
runtime prompts, exception strings, or parsing behavior. They are therefore
retained byte-faithfully and checksummed instead of silently rewritten.
In particular, the accepted QR-code project intentionally tests a Unicode
fixture containing code points U+4E16 and U+754C; rewriting that generated
fixture would invalidate the accepted/replay repository hashes and weaken the
baseline evidence chain.

Nested VCS administrative metadata is not experimental source or an
observation and is omitted from the newly imported baseline package. This
matches the campaign's canonical tree-hash policy, which excludes `.git`.

First-party comments, reviewer documentation, configuration annotations, and
report labels outside those immutable scopes were normalized to English. This
now includes the active RQ1 model runtime, its synchronized DT copy, and the
RQ2 SrcMarker source copy. Obsolete multilingual manual server tests were
removed; they were not invoked by any released experiment or reproduction
entry point. The only experiment fixture touched in executable RQ1 campaign
code was rewritten as an equivalent Unicode escape, preserving its runtime
value. No raw result, prediction, checkpoint, prompt response, or statistical
value was translated.

Exact local source-normalization details and pre/post hashes are recorded in
`patches/LANGUAGE_NORMALIZATION.md`.
