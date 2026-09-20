import os
from datasets import load_dataset

# Download the CodeSearchNet Java subset.
dataset = load_dataset('code_search_net', 'java')

# Save it in JSONL format.
import json
output_dir = './java_data'
os.makedirs(output_dir, exist_ok=True)

with open(f'{output_dir}/java_train.jsonl', 'w') as f:
    for sample in dataset['train']:
        # print(sample)
        json.dump({'code': sample['whole_func_string']}, f)
        f.write('\n')
