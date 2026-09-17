# Training-cost evidence

The two logs are the canonical seed-42, 25-epoch CSN-JavaScript fresh-training
runs used by RQ2 and the semantic-preserving rows of Table X. The reproduction
script defines one-time training cost as the interval from the first to the
last timestamped log record, thereby including data/model initialization and
the final per-epoch test pass. `training_times.csv` is regenerated from these
logs.
