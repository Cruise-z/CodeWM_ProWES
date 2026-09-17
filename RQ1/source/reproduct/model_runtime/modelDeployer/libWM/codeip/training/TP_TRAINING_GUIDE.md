# TP 模型训练脚本使用说明

## 概述

`train_tp_model.py` 是一个适配本仓库的类型预测器 (Type Predictor, TP) 训练脚本。
它使用 CodeSearchNet 数据集中的代码，通过 Pygments 词法分析，学习预测下一个词法类别的 LSTM 模型。

## 前提条件

### 安装依赖

```bash
pip install torch transformers pygments datasets tqdm
```

### 准备 CodeSearchNet Java 数据集

**方式1：直接下载预处理的 JSONL 文件**

从 [CodeSearchNet GitHub](https://github.com/github/CodeSearchNet) 下载 Java 数据集，或使用 Hugging Face datasets：

```python
from datasets import load_dataset

# 下载 CodeSearchNet Java 子集
dataset = load_dataset('code_search_net', 'java')

# 保存为 JSONL 格式
import json
output_dir = './java_data'
os.makedirs(output_dir, exist_ok=True)

with open(f'{output_dir}/java_train.jsonl', 'w') as f:
    for sample in dataset['train']:
        json.dump({'code': sample['code']}, f)
        f.write('\n')
```

**方式2：使用现有的本地代码文件**

如果已有本地 Java 代码文件，可先转换为 JSONL 格式：

```python
import json
from pathlib import Path

code_dir = './java_source_code'  # 包含 .java 文件的目录
output_file = './java_data/java_train.jsonl'

Path(output_file).parent.mkdir(parents=True, exist_ok=True)

with open(output_file, 'w') as f:
    for java_file in Path(code_dir).rglob('*.java'):
        try:
            code = java_file.read_text(encoding='utf-8')
            json.dump({'code': code}, f)
            f.write('\n')
        except:
            continue
```

## 使用方法

### 基本用法

```bash
python train_tp_model.py \
    --data_dir ./java_data \
    --language java \
    --output_dir ./models
```

### 完整参数说明

#### 数据相关参数

- `--data_dir` (required): JSONL 文件所在目录
- `--language`: 编程语言 (default: java，可选: python, go, javascript, php)
- `--seq_length`: 序列长度，即每次训练用多长的词法类别序列 (default: 30)

#### 模型超参数

- `--embed_size`: 嵌入维度 (default: 64)
- `--hidden_size`: LSTM 隐藏层维度 (default: 128)

#### 训练相关参数

- `--batch_size`: 批大小 (default: 128)
- `--learning_rate`: 学习率 (default: 0.001)
- `--weight_decay`: L2 正则化系数 (default: 1e-5)
- `--epochs`: 最大训练轮数 (default: 20)
- `--patience`: 早停等待轮数 (default: 3)

#### 其他参数

- `--device`: 训练设备 (default: cuda，如无 GPU 自动切换到 cpu)
- `--num_workers`: 数据加载线程数 (default: 4)
- `--output_dir`: 模型保存目录 (default: 当前目录)

### 示例

**使用较大的模型和更多轮次**

```bash
python train_tp_model.py \
    --data_dir ./java_data \
    --language java \
    --embed_size 128 \
    --hidden_size 256 \
    --batch_size 64 \
    --learning_rate 0.0005 \
    --epochs 30 \
    --output_dir ./models
```

**快速测试（小数据集）**

```bash
python train_tp_model.py \
    --data_dir ./java_data \
    --language java \
    --batch_size 32 \
    --epochs 5 \
    --output_dir ./models
```

## 输出

训练完成后，在 `--output_dir` 目录下会生成：

```
lstm_model_java.pth    # 最佳模型权重（验证集准确率最高时保存）
```

这个文件可直接被 `wm.py` 中的以下代码加载：

```python
lstm_model = LSTMModel(vocab_size, embed_size, hidden_size, output_size)
lstm_model.load_state_dict(torch.load("lstm_model_java.pth"))
```

## 训练过程说明

1. **数据加载**：从 JSONL 文件逐行读取代码
2. **词法分析**：使用 Pygments 对代码进行词法分析，提取词法类别序列
3. **滑动窗口**：将长序列转换为长度为 `seq_length` 的监督样本对 (input, target)
4. **训练**：使用 Adam 优化器最小化交叉熵损失
5. **验证**：在验证集上评估模型
6. **早停**：若验证集准确率连续 `patience` 轮不改进，则停止训练
7. **保存**：保存验证集准确率最高的模型

## 故障排查

**问题1：找不到 JSONL 文件**

```
ValueError: No JSONL files found in ./java_data
```

**解决方案**：确保 JSONL 文件存在，并检查路径是否正确

```bash
ls -la ./java_data/
```

**问题2：显存不足**

```
RuntimeError: CUDA out of memory
```

**解决方案**：减小 batch_size 或 hidden_size

```bash
python train_tp_model.py \
    --data_dir ./java_data \
    --language java \
    --batch_size 32 \
    --hidden_size 64 \
    --output_dir ./models
```

**问题3：数据集太小**

```
Dataset too small, may not train effectively
```

**解决方案**：确保至少有足够的代码样本。对于有效的模型训练，建议至少 10,000 个代码样本。

## 与主仓库的整合

训练完成后，将生成的 `lstm_model_java.pth` 放在与 `wm.py` 相同的目录，或修改 `wm.py` 中加载路径：

```python
# 在 wm.py 中
lstm_model.load_state_dict(torch.load("path/to/lstm_model_java.pth"))
```

然后正常运行水印脚本即可。

## 模型性能指标

训练期间会输出以下指标：

- **Train Loss**: 训练损失（越低越好）
- **Train Acc**: 训练集准确率（越高越好）
- **Val Loss**: 验证集损失
- **Val Acc**: 验证集准确率（用于早停判断）

通常，对于词法类别预测任务，验证集准确率可达到 60%-85% 取决于数据质量和模型容量。
