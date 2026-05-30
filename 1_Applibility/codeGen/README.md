# Code Generation Guide

------

## ==File structure layout==

```bash
├── patches
│   └── MetaGPT
│       └── metagpt
│           ├── actions
│           │   ├── action.py
│           │   ├── architecture_guidance_an.py
│           │   ├── design_api_an.py
│           │   ├── project_management_an.py
│           │   ├── protocol_contracts_an.py
│           │   ├── protocol_shared_an.py
│           │   ├── write_code.py
│           │   └── write_prd_an.py
│           ├── provider
│           │   └── base_llm.py
│           ├── README.md
│           ├── roles
│           │   ├── di(main Branch)
│           │   │   ├── engineer2.py
│           │   │   └── README.md
│           │   └── engineer.py
│           └── software_company.py
├── prompts
│   ├── cpp
│   │   ├── brickBreaker.py
│   │   ├── __init__.py
│   │   └── tankBattle.py
│   ├── __init__.py
│   ├── java
│   │   ├── ...
│   └── python
│       ├── ...
├── README.md
└── scripts
    ├── agentArchGen.py
    ├── agentCodeGen.py
    ├── agent.py
    ├── batchCodeGenDT.py
    └── modelDeploy
        ├── countTokens.py
        ├── modelDeployer
        │   ├── ...
```

### Repository Organization

This repository is organized into three major components: `patches`, `prompts`, and `scripts`.

#### `patches/`

The `patches` directory contains customized versions of selected scripts from mature open-source projects. In particular, `patches/MetaGPT` stores modified MetaGPT scripts that are adapted to support our own code generation workflow. These files follow the original directory structure of the upstream MetaGPT project, making it easier to compare the customized implementation with the original source code and to identify which components have been modified.

The modifications mainly involve adapting the original MetaGPT workflow, roles, actions, and LLM provider interfaces to support customized generation protocols, local model invocation, and task-specific code generation behavior. In particular, the customized MetaGPT scripts under `patches/MetaGPT` include language-specific testing protocols for Java, Python, and C++ projects, which define the required build file, runtime entry, test target, and test command for each generated repository, thereby standardizing the generation and evaluation process across different programming languages.

| Language | Build File         | Runtime Entry             | Protocol Test Target          | Test Command |
| -------- | ------------------ | ------------------------- | ----------------------------- | ------------ |
| Java     | `pom.xml`          | `src/main/java/Main.java` | `src/test/java/MainTest.java` | `mvn test`   |
| Python   | `requirements.txt` | `Main.py`                 | `tests/test_main.py`          | `pytest`     |
| C++      | `CMakeLists.txt`   | `src/Main.cpp`            | `tests/test_main.cpp`         | `ctest`      |

By enforcing these protocols, the modified MetaGPT workflow ensures that generated repositories are buildable, runnable, and testable in an automated evaluation environment.

#### `prompts/`

The `prompts` directory stores project-level prompts used to generate target code repositories for evaluation. The prompts are organized by programming language, such as `cpp`, `java`, and `python`. Each prompt file **mainly describes the functional requirements and expected behavior of the target project**, ==while file structure, runtime entry, build configuration, and testing protocol are enforced separately by the customized MetaGPT framework.==

These prompts are used as controlled inputs for generating different types of code repositories, ensuring that the generated projects follow consistent structural and execution requirements across languages and tasks.

#### `scripts/`

The `scripts` directory contains the main execution scripts for code generation. These scripts support two primary generation settings:

1. **Prompt-based code generation**, where a target repository is generated directly from a predefined project prompt.
2. **Architecture-guided code generation**, where the generation process is guided by the architecture or structure of an existing repository.

The top-level scripts are responsible for coordinating the generation pipeline, invoking the corresponding agents, loading prompts, and managing batch generation tasks.

##### `scripts/modelDeploy/`

The `scripts/modelDeploy` directory contains components related to local model deployment. It includes the local model serving engine, deployment utilities, and the logits processors of all watermarking methods integrated into the generation engine for evaluation.

This component is used to run local LLM-based code generation and to apply different code watermarking strategies during decoding. It provides the infrastructure required for testing watermark embedding behavior under a unified local deployment setting.

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
