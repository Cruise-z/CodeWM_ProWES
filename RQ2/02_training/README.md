# Fresh training

Canonical code is `../source/training/SrcMarker_fresh/`. Exact final artifacts
are under `../../results/RQ2/02_training/`: eight best checkpoints, eight run
manifests, eight 25-epoch histories, clean per-sample predictions, training
logs, and pipeline logs. Only `models_best.pt` is retained because it is the
checkpoint used for every formal detector run; redundant `models_24.pt` and
`models_final.pt` copies are excluded.
