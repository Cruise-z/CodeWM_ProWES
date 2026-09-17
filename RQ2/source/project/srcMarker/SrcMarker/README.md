# Script Usage Guide

## Move the Scripts

Place the scripts in this directory, `2_Robustness/project/srcMarker/SrcMarker/`, into the corresponding `SrcMarker/` directory in the source repository.

## Workflow

### Train and Evaluate

Train the model using the original repository's procedure, then run watermark extraction evaluation:

```bash
# --write_output controls whether to write results to ./results directory
# the results could be used in null-hypothesis test
python eval_main.py \
    --checkpoint_path <path_to_model_checkpoint> \
    --lang java \
    --dataset csn_java \
    --dataset_dir ./datasets/csn_java \
    --n_bits 4 \
    --model_arch=gru \
    --shared_encoder \
    --write_output
```



### Obfuscation

Obfuscate the post-extraction results under `SrcMarker/results`:

```bash
## Example obfuscation script invocation
python 1_obfus.py \
	--sample \
	--sample_size 10
```



### Watermark Extraction After Obfuscation

- Before use, write the obfuscated file (that is, a JSONL file containing the `"after_obfus"` field) into:

  `SrcMarker/datasets/csn_java/obfus.jsonl`

- The default output directory is: `SrcMarker/results_obfus`

```bash
python 2_eval_obfus.py\
	--checkpoint_path ./ckpts/4bit_gru_srcmarker_42_csn_java/models_best.pt \
    --lang java \
    --dataset csn_java \
    --dataset_dir ./datasets/csn_java/ \
    --n_bits 4 \
    --model_arch=gru \
    --shared_encoder \
    --output_filename java_4bit_obfus_ai_GPT_paid_rules1.jsonl
```



### Obfuscation Statistics

```bash
python 3_analysis.py
```
