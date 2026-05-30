#=====================================Basic Environment Configuration=====================================#
import os
# os.chdir("/home/zhaorz/project/CodeWM/sweet-watermark/DT/workspace")

# 1) Route official OpenAI through proxy (adjust port based on your proxy setup)
os.environ["HTTPS_PROXY"] = os.environ.get("HTTPS_PROXY", "http://127.0.0.1:7890")
os.environ["HTTP_PROXY"]  = os.environ.get("HTTP_PROXY",  "http://127.0.0.1:7890")
# Some environments read ALL_PROXY, so set it uniformly as well
os.environ["ALL_PROXY"]   = os.environ.get("ALL_PROXY",   os.environ["HTTPS_PROXY"])

# 2) Always allow local loopback addresses to connect directly (bypass proxy)
no_proxy = set(filter(None, os.environ.get("NO_PROXY", "").split(",")))
no_proxy.update({"127.0.0.1", "localhost", "::1"})
os.environ["NO_PROXY"] = ",".join(no_proxy)
os.environ["no_proxy"] = os.environ["NO_PROXY"]  # Compatible with lowercase
#=====================================Basic Environment Configuration=====================================#

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
    
    # 1) Load two sets of configurations (consistent with official examples)
    local_vllm = Config.default()                      # From ~/.metagpt/config2.yaml
    gpt_openai = Config.from_home("openai.yaml")       # From ~/.metagpt/local_vllm.yaml
    try:
        local_vllm.llm.timeout = max(getattr(local_vllm.llm, "timeout", 0) or 0, 1200)
        # Some commits use request_timeout field:
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
    
    # Other roles
    pm, arch, pmgr = ProductManager(config=gpt_openai), Architect(config=gpt_openai), ProjectManager(config=gpt_openai)
    # Engineer uses derived class (internal fixed code writing action to local)
    eng = Engineer(config=local_vllm)
    # eng = DataInterpreter(config=local_vllm)
    eng.llm.config.__dict__["xargs"] = xargs

    team = Team(env=Environment(desc=prompts.java.snakegame.desc), roles=[pm, arch, pmgr, eng])
    idea = prompts.java.snakegame.idea

    await team.run(n_round=5, idea=idea)
    
if __name__ == "__main__":
    asyncio.run(main())