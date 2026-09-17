# Environment records

- `preflight.json`: RQ1 host, hardware, Python packages, model runtime,
  tokenizer/weights, container inspection, and executable version probes.
- `model_weights.json` and `model_replicas.json`: RQ1 model identity and replica
  consistency.
- `rq2_environment.json`: RQ2 seed, payload size, parser identity, input and
  checkpoint hashes, and bootstrap protocol.
- `requirements_rq2.txt`: minimum packages for the revised RQ2 attack layer.

The RQ1 workspace did not supply a standalone lockfile. Its preflight package
inventory is the authoritative record of the executed environment; this is
listed as a packaging limitation rather than replaced by guessed pins.
