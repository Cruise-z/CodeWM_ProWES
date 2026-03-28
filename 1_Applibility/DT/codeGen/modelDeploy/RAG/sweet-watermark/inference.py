import math
from typing import List, Dict, Optional

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from transformers.generation.logits_process import PrefixConstrainedLogitsProcessor, LogitsProcessorList
from structDB import retrieve_reference
from utils import *
import os
# os.environ["CUDA_LAUNCH_BLOCKING"] = "1"

from watermark import WatermarkLogitsProcessor
from sweet import SweetLogitsProcessor

# 1) Initialize the engine (replaceable with any HF CausalLM)
engine = HFModelEngine(
    model_name="bigcode/starcoder",   # Change the model here
    device_map=None,                  # Single GPU is the safest; use "auto" if sharding is needed
    fp16=True,
)

wllm_processor = WatermarkLogitsProcessor(vocab=list(engine.tokenizer.get_vocab().values()),
                                               gamma=0.5,
                                               delta=1)

sweet_processor = SweetLogitsProcessor(vocab=list(engine.tokenizer.get_vocab().values()),
                                       gamma=0.5,
                                       delta=1,
                                       entropy_threshold=0.9)

# 2) Adapt your retriever
retriever = FunctionRetriever(retrieve_reference)

# 3) Orchestrator
rag_gen = RagConstrainedGenerator(engine, retriever)

prompt = "Task: Brick breaker game\nPrompt:use java Create a brick breaker game\nrequirements:\n• Game Board:\n⋄ Create a game board with a grid-based layout.\n..."
prefix = "package correct;\n\nimport javax.swing.*;\nimport java.awt.*;\nimport java.awt.event.ActionEvent;\nimport java.awt.event.ActionListener;\nimport java.awt.event.KeyEvent;\nimport java.awt.event.KeyListener;\nimport java.util.ArrayList;\nimport java.util.Random;\n\npublic class BrickBreakerGame extends JPanel implements ActionListener, KeyListener {\n"

# A) Adaptive soft constraint (recommended; effectively equivalent to hard clamping but expressed as a "soft" form):
res = rag_gen.generate(
    prompt, prefix,
    top_k=1,
    constraint="adaptive",    # 'adaptive' | 'fixed' | 'hard'
    gamma = 2.5,
    alpha = 0.65,
    lambda_start = 1.0,
    lambda_end = 1.0,
    schedule = "constant",   # "constant" | "linear"
    max_bias = 50.0,
    eps = 1e-12,
    compute_in_fp32 = False,
    finish_with_eos = True,
    ensure_copy = False,
    gamma_safe = 1e-6,
    fixed_bias = 12.0,
    # watermark_processor = None,
    watermark_processor=sweet_processor  # Replace this with your own watermark processor if needed
)
print(res["rag_meta"]["rank"], res["rag_meta"]["route"], res["rag_meta"]["task_name"], res["rag_meta"]["score"])
print(res["rag_meta"]["reference"])
print(res["route"], res["exact_match"], len(res["text"]))
print(res["text"])

# B) Fixed-bias soft constraint:
# res2 = rag_gen.generate(prompt, prefix, constraint="fixed", fixed_bias=16.0)
# print(res2["route"], res2["exact_match"], len(res2["text"]))

# C) Hard clamping (100% consistent, used for extreme control comparisons):
# res3 = rag_gen.generate(prompt, prefix, constraint="hard")
# print(res3["route"], res3["exact_match"], len(res3["text"]))
