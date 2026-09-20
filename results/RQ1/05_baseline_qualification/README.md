# RQ1 baseline qualification evidence

This directory preserves the final evidence for the 42
project-language baselines used by RQ1. It closes the qualification chain:

```text
campaign configuration and seed
  -> 88 generation attempts (42 pass, 46 fail)
  -> 42 accepted repository snapshots
  -> 42 same-seed regeneration replays
  -> evaluator logs and canonical repository-tree hashes
  -> campaign audit
```

## Reviewer entry points

- `ledger/results.csv` is the original 42-unit campaign result ledger. Its
  `attempt_count` column sums to 88.
- `indexes/attempt_ledger.csv` is a flattened index of all 88 immutable
  per-attempt `evidence.json` files.
- `indexes/accepted_ledger.csv` indexes all 42 accepted seeds, evidence files,
  and canonical repository snapshots.
- `indexes/replay_ledger.csv` indexes all 42 replay runs, including the
  accepted/replay tree hashes and the identity decision.
- `ledger/audit.json` is the original final campaign audit (`complete: true`,
  no issues).
- `logs/` contains the two seed-search and two replay worker logs.

Each attempt and replay directory retains its original generation report,
evaluator log, generated project tree, and execution artifacts. Nested VCS
administrative directories are omitted because the campaign hash excludes
`.git` and they contain no experimental observation. Each accepted directory
retains `seed.json`, `evidence.json`, and the canonical repository.
Absolute workspace paths inside immutable JSON evidence record the execution
host; the adjacent relative paths and indexes are the portable artifact entry
points.

## Verification

From the artifact root, run:

```bash
python3 tools/build_rq1_baseline_ledgers.py
python3 tools/verify_rq1_evidence.py
```

The verifier checks the 88/42/42 cardinalities, all ledger-to-evidence links,
generation-report and evaluator-log digests, accepted and replay repository
tree hashes, same-seed replay identity, campaign-level hashes, and the derived
indexes. The tree-hash algorithm is the frozen implementation in
`RQ1/source/reproduct/campaign.py`; build outputs, evaluator output directories,
and local VCS metadata are deliberately excluded by that canonical algorithm.

## Scope

This package contains only the final paper-reported campaign: 88 attempts, 42
accepted repositories, and 42 verified replays. The exact import scope and
source revision are recorded in `PROVENANCE.json`.
