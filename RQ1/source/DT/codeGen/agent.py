# =============================== Environment setup ===============================
import os
# os.chdir("/home/zhaorz/project/CodeWM/sweet-watermark/DT/workspace")

# 1) Route the hosted OpenAI endpoint through the configured local proxy.
os.environ["HTTPS_PROXY"] = os.environ.get("HTTPS_PROXY", "http://127.0.0.1:7890")
os.environ["HTTP_PROXY"]  = os.environ.get("HTTP_PROXY",  "http://127.0.0.1:7890")
# Some clients read ALL_PROXY, so keep it consistent.
os.environ["ALL_PROXY"]   = os.environ.get("ALL_PROXY",   os.environ["HTTPS_PROXY"])

# 2) Always connect to loopback addresses directly.
no_proxy = set(filter(None, os.environ.get("NO_PROXY", "").split(",")))
no_proxy.update({"127.0.0.1", "localhost", "::1"})
os.environ["NO_PROXY"] = ",".join(no_proxy)
os.environ["no_proxy"] = os.environ["NO_PROXY"]  # Lowercase compatibility.
# =============================== Environment setup ===============================

import prompts
import asyncio, json, httpx
from openai import AsyncOpenAI
from metagpt.config2 import Config
from metagpt.actions.write_code import WriteCode
from metagpt.roles.engineer import Engineer
# from metagpt.roles.di.data_interpreter import DataInterpreter
from metagpt.roles.product_manager import ProductManager
from metagpt.roles.architect import Architect
from metagpt.roles.project_manager import ProjectManager
from metagpt.team import Team
from metagpt.environment import Environment

async def main():

    # 1) Load both configurations, following the upstream MetaGPT example.
    local_vllm = Config.default()                      # ~/.metagpt/config2.yaml
    gpt_openai = Config.from_home("openai.yaml")       # ~/.metagpt/openai.yaml
    try:
        local_vllm.llm.timeout = max(getattr(local_vllm.llm, "timeout", 0) or 0, 1200)
        # Some MetaGPT revisions use the request_timeout field.
        if hasattr(local_vllm.llm, "request_timeout"):
            local_vllm.llm.request_timeout = max(getattr(local_vllm.llm, "request_timeout", 0) or 0, 1200)
    except Exception:
        pass

    xargs = {
        "temperature": 0.7,
        "max_tokens": 4096,
        "parallel": True,
        "rng_seed": 123456,
        "internal_processor_names": [],
        "external_processor_names": ["sweet"],
        "external_processor_params": {
            "sweet": {"gamma": 0.7, "delta": 2, "entropy_threshold": 0.85},
            "wllm": {"gamma": 0.4, "delta": 1},
        },
    }

    # Other roles.
    pm, arch, pmgr = ProductManager(config=gpt_openai), Architect(config=gpt_openai), ProjectManager(config=gpt_openai)
    # The Engineer subclass pins code writing to the local model.
    eng = Engineer(config=local_vllm)
    # eng = DataInterpreter(config=local_vllm)
    eng.llm.config.__dict__["xargs"] = xargs

    team = Team(env=Environment(desc=prompts.java.snakegame.desc), roles=[pm, arch, pmgr, eng])
    idea = prompts.java.snakegame.idea

    await team.run(n_round=5, idea=idea)

if __name__ == "__main__":
    asyncio.run(main())
