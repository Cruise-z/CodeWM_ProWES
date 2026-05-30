# Code Generation Guide

------





## ==Agent Architecture==

The code generation workflow is assisted by `agent:MetaGPT`.

Within MetaGPT's `[Action] -> [Role]` framework, different models are assigned to different roles:

- Project architecture design: handled by the official `openai` models `gpt-4` / `gpt-4o`

- Code generation: handled by the locally deployed `Qwen/Qwen2.5-Coder-32B-Instruct` and `Qwen3-Coder-30B-A3B-
  Instruct`
  
  > `Qwen/Qwen2.5-Coder-32B-Instruct` and `Qwen3-Coder-30B-A3B-
  > Instruct` is currently one of the strongest open-source models for code generation.
  > Reference: [`Hugging Face` open-source code model leaderboard](https://huggingface.co/spaces/bigcode/bigcode-models-leaderboard)

### `config` Setup

The `config` files for the two models are shown below:

- Official `openai` model:

  ```bash
  (base) zhaorz@rubick:~/.metagpt$ cat openai.yaml 
  llm:
    api_type: openai
    base_url: https://api.chatanywhere.tech/v1
    # base_url: http://127.0.0.1:8000/v1
    api_key: sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    model: gpt-4
    # model: NTQAI/Nxcode-CQ-7B-orpo
    # model: Qwen/Qwen2.5-Coder-32B-Instruct 
    use_proxy: true
    stream: true
  ```

- Local open-source model (default configuration):

  ```bash
  (base) zhaorz@rubick:~/.metagpt$ cat config2.yaml 
  llm:
    api_type: open_llm                  
    base_url: http://127.0.0.1:8000/v1
    model: Qwen/Qwen2.5-Coder-32B-Instruct
    # model: NTQAI/Nxcode-CQ-7B-orpo     
    api_key: EMPTY
    use_proxy: false
    stream: false
    timeout: 1200
    # request_timeout: 1200
  repair_llm_output: true
  ```

### `prompt` Design

Prompts for different projects have been organized under the `./prompts` directory.

### Configure Parameters and Run

For convenience, frequently adjusted **generation parameters** and **watermark-related parameters** are placed in the `xargs` field.

Example `xargs` configuration:

```python
xargs = {
    "temperature": 0.7,
    "max_tokens": 4096,
    "parallel": True,
    "rng_seed": 123456,
    "internal_processor_names": [],
    "external_processor_names": ["sweet"],
    "external_processor_params": {
        "sweet": {"gamma": 0.5, "delta": 5, "entropy_threshold": 0.60},
        "wllm": {"gamma": 0.4, "delta": 1},
    },
}
```



------

## ==Generate from Prompts==

Update the `xargs` parameters in `./agent.py` and run it.

------

## ==Generate from a Framework==

After generating a high-quality, usable project architecture with MetaGPT in ==Generate from Prompts== mode, you can reuse that architecture for code generation as follows:

- Run `./agentArchGen.py`: first generate a high-quality reusable architecture repository with the `openai` model
- Run `./agentCodeGen.py`: then generate customized code on top of that architecture repository using the open-source model

**Notes:**

- It is recommended to back up a usable architecture repository once it has been generated, so it can be reused for multiple code-generation runs later.
- Standard example architecture repositories are provided under `./MetaGPT/workspace`.
