# Baseline qualification

Implementation: `../source/reproduct/campaign.py`.

The code enforces complete generation, no truncation, evaluator return code 0,
checkpoint scoping, accepted-seed capture, and same-seed/hash replay.
The complete final evidence is released at
`../../results/RQ1/05_baseline_qualification/`: 88 per-attempt records, 42
accepted repositories, and 42 verified replays, together with generation
reports, evaluator logs, hashes, and flattened reviewer indexes.

Run `python3 ../../tools/verify_rq1_evidence.py` from this directory, or
`python3 tools/verify_rq1_evidence.py` from the artifact root, to validate the
full ledger and replay chain.
