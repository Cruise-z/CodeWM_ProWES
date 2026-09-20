# CodeIP type-predictor training

`train_tp_model.py` trains the optional CodeIP lexical type predictor on Java
code. The released Table X campaign uses CodeIP's random-message branch and
does not load this optional predictor.

## Data

Prepare a JSONL CodeSearchNet Java split, or use `dataset.py` to download and
materialize the Java subset. Each training example is converted to a lexical
category sequence with Pygments and split into fixed-length supervised windows.

## Run

```bash
python train_tp_model.py \
  --data_dir /path/to/codesearchnet-java \
  --language java \
  --seq_length 30 \
  --batch_size 128 \
  --learning_rate 0.001 \
  --weight_decay 1e-5 \
  --epochs 20 \
  --patience 3 \
  --device cuda \
  --output_dir ./checkpoints
```

The script reports training/validation loss and accuracy, applies early
stopping, and writes `lstm_model_java.pth` for the best validation epoch. Place
the checkpoint under the CodeIP checkpoint directory before enabling PDA mode.

For a smoke test, reduce the dataset size and epoch count. For a released
experiment, record the dataset revision, split IDs, seed, full configuration,
training log, best epoch, and checkpoint SHA-256.
