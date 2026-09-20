from dataclasses import dataclass, field
from typing import List

@dataclass
class WmBaseArgs:
    temperature: float = 0.75 
    # model_name: str = "Qwen/Qwen2.5-Coder-32B-Instruct"
    model_name: str = "NTQAI/Nxcode-CQ-7B-orpo"
    language: str = "java"
    sample_num: int = 1000
    sample_seed: int = 42
    seed: int = 42
    num_beams: int = 1
    delta: float = 5.0
    gamma: float = 3.0
    repeat_penalty: float = 1.2
    ngram_size: int = 10
    message: List[int] = field(default_factory=lambda: [2024])
    prompt_length: int = 128
    generated_length: int = 200
    message_code_len: int = 20 
    encode_ratio: float = 10.
    top_k: int = 1000
    dataset_name: str = 'codebleu'  # Dataset selection: 'c4' or 'codebleu'.
    use_pda: bool = False  # Whether to use the PDA type predictor.
    device: str = 'cuda'
    save_path: str = "../results.json"
