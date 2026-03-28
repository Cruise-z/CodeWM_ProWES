import json
from transformers import AutoTokenizer

# Load the tokenizer
tokenizer = AutoTokenizer.from_pretrained("bigcode/starcoder")

# Read the JSONL file and count tokens for each record
def load_data_and_count_tokens(file_path):
    with open(file_path, 'r') as file:
        for line in file:
            data = json.loads(line.strip())
            # Use "prompt" + "prefix" as the input text
            input_text = data.get('prompt', '') + " " + data.get('prefix', '')
            # Count tokens
            tokenized_input = tokenizer(input_text)
            token_count = len(tokenized_input['input_ids'])  # Number of tokens
            print(f"Task ID: {data['task_id']}, Token count: {token_count}")

# Example usage
input_file = './datasets/projectDev_java.jsonl'  # Replace with your JSONL file path
load_data_and_count_tokens(input_file)
