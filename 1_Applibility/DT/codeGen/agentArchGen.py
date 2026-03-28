#=====================================Basic Environment Setup=====================================#
import os
# os.chdir("/home/zhaorz/project/CodeWM/sweet-watermark/DT/workspace")

# 1) Route official OpenAI traffic through the proxy (adjust the port as needed)
os.environ["HTTPS_PROXY"] = os.environ.get("HTTPS_PROXY", "http://127.0.0.1:7890")
os.environ["HTTP_PROXY"]  = os.environ.get("HTTP_PROXY",  "http://127.0.0.1:7890")
# Some environments also read ALL_PROXY, so set it as well
os.environ["ALL_PROXY"]   = os.environ.get("ALL_PROXY",   os.environ["HTTPS_PROXY"])

# 2) Always bypass the proxy for local loopback addresses
no_proxy = set(filter(None, os.environ.get("NO_PROXY", "").split(",")))
no_proxy.update({"127.0.0.1", "localhost", "::1"})
os.environ["NO_PROXY"] = ",".join(no_proxy)
os.environ["no_proxy"] = os.environ["NO_PROXY"]  # Lowercase compatibility
#=====================================Basic Environment Setup=====================================#

import prompts
import asyncio, json, httpx
from openai import AsyncOpenAI
from pathlib import Path
from metagpt.config2 import Config
from metagpt.context import Context
from metagpt.actions.write_code import WriteCode
from metagpt.roles.engineer import Engineer
# from metagpt.roles.di.data_interpreter import DataInterpreter
from metagpt.roles.product_manager import ProductManager
from metagpt.roles.architect import Architect
from metagpt.roles.project_manager import ProjectManager
from metagpt.team import Team
from metagpt.environment import Environment
        
async def main():
    
    # 1) Load the two configurations (aligned with the official example)
    local_vllm = Config.default()                      # From ~/.metagpt/config2.yaml
    # TODO: set the local code-generation model base_url to an invalid value to trigger MetaGPT snapshot generation
    local_vllm.llm.base_url = "http://127.0.0.1:8000/v0"
    gpt_openai = Config.from_home("openai.yaml")       # From ~/.metagpt/local_vllm.yaml
    try:
        local_vllm.llm.timeout = max(getattr(local_vllm.llm, "timeout", 0) or 0, 1200)
        # Some revisions use the request_timeout field:
        if hasattr(local_vllm.llm, "request_timeout"):
            local_vllm.llm.request_timeout = max(getattr(local_vllm.llm, "request_timeout", 0) or 0, 1200)
    except Exception:
        pass
    
    # Other roles
    pm, arch, pmgr = ProductManager(config=gpt_openai), Architect(config=gpt_openai), ProjectManager(config=gpt_openai)
    # The engineer uses a derived class that pins code writing to the local model
    eng = Engineer(config=local_vllm)
    # eng = DataInterpreter(config=local_vllm)

    team = Team(
        env=Environment(desc=prompts.java.snakegame.desc), 
        roles=[pm, arch, pmgr, eng]
    )
    idea = prompts.java.snakegame.idea
    
    await team.run(n_round=5, idea=idea)
    
    
if __name__ == "__main__":
    asyncio.run(main())
