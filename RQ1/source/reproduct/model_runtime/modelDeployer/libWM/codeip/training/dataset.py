import os
from datasets import load_dataset

# 下载 CodeSearchNet Java 子集
dataset = load_dataset('code_search_net', 'java')

# 保存为 JSONL 格式
import json
output_dir = './java_data'
os.makedirs(output_dir, exist_ok=True)

with open(f'{output_dir}/java_train.jsonl', 'w') as f:
    for sample in dataset['train']:
        # print(sample)
        json.dump({'code': sample['whole_func_string']}, f)
        f.write('\n')