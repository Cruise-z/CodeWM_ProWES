# 脚本使用说明

## 移动脚本

将本目录`2_Robustness/project/srcMarker/SrcMarker/`下的脚本放在源仓库对应目录`SrcMarker/`下即可

## 操作方法

### 训练并评估

按照原仓库中的方法对模型进行训练，并进行水印提取评估：

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



### 混淆操作

对`SrcMarker/results`下的水印提取后结果进行混淆：

```bash
##混淆脚本调用示例
python 1_obfus.py \
	--sample \
	--sample_size 10
```



### 混淆后水印提取

- 使用前，将混淆后(即json列表中含有"after_obfus"字段的文件)写入：

  `SrcMarker/datasets/csn_java/obfus.jsonl`中即可

- 默认输出文件夹是：`SrcMarker/results_obfus`

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



### 混淆统计

```bash
python 3_analysis.py
```

