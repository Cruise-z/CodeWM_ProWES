#=====================================Basic environment setup=====================================#
import os
import json
from typing import List, Any
# os.chdir("/home/zhaorz/project/CodeWM/sweet-watermark/DT/workspace")

# 1) Route official OpenAI traffic through a proxy (adjust the port for your own proxy)
os.environ["HTTPS_PROXY"] = os.environ.get("HTTPS_PROXY", "http://127.0.0.1:7890")
os.environ["HTTP_PROXY"]  = os.environ.get("HTTP_PROXY",  "http://127.0.0.1:7890")
# Some environments read ALL_PROXY as well; set it consistently
os.environ["ALL_PROXY"]   = os.environ.get("ALL_PROXY",   os.environ["HTTPS_PROXY"])

# 2) Always bypass the proxy for loopback addresses (direct connection)
no_proxy = set(filter(None, os.environ.get("NO_PROXY", "").split(",")))
no_proxy.update({"127.0.0.1", "localhost", "::1"})
os.environ["NO_PROXY"] = ",".join(no_proxy)
os.environ["no_proxy"] = os.environ["NO_PROXY"]  # compatibility for lowercase
#=====================================Basic environment setup=====================================#

import asyncio
import re
import secrets
from pathlib import Path
from types import SimpleNamespace
from metagpt.config2 import Config
from metagpt.context import Context
from metagpt.team import Team
from metagpt.roles.engineer import Engineer, extract_and_remove_tagContent
from metagpt.actions.write_code import WriteCode
from metagpt.utils.git_repository import GitRepository
from metagpt.utils.project_repo import ProjectRepo
from metagpt.utils.git_repository import GitRepository
from metagpt.utils.project_repo import ProjectRepo
from metagpt.schema import Document

def make_seed(bits: int = 32) -> int:
    """Return a random seed in [1, 2**bits - 1] (avoid 0)."""
    s = 0
    while s == 0:
        s = secrets.randbits(bits)
    return s

async def _run_actions_manually(company: Team, eng: Engineer, actions: List[WriteCode]):
    """
    Execute WriteCode instances one by one directly, bypassing Team scheduling differences.
    Bind context/env/llm/rc to each action to ensure run() has all dependencies.
    """
    ctx = getattr(company, "context", None)
    env = getattr(company, "env", None)
    # Pick an available LLM: prefer Engineer.llm, otherwise Context.config.llm
    llm = getattr(eng, "llm", None)
    if llm is None:
        try:
            llm = getattr(getattr(ctx, "config", None), "llm", None)
            if llm is not None:
                setattr(eng, "llm", llm)
        except Exception:
            pass

    # ★ Key fix: inject company.context.repo / git_repo into the context used by actions
    repo_obj = getattr(getattr(company, "context", None), "repo", None)
    git_repo = getattr(repo_obj, "git_repo", None) if repo_obj is not None else None
    # Inject into context
    if ctx is not None and repo_obj is not None:
        try:
            if getattr(ctx, "repo", None) is None:
                ctx.repo = repo_obj
        except Exception:
            ctx.__dict__["repo"] = repo_obj
    if ctx is not None and git_repo is not None:
        try:
            ctx.git_repo = git_repo
        except Exception:
            ctx.__dict__["git_repo"] = git_repo
    # Debug: verify workdir availability
    try:
        print(">> ctx.git_repo.workdir =", getattr(getattr(ctx, "git_repo", None), "workdir", None))
    except Exception:
        pass
    
    for i, act in enumerate(actions, 1):
        # --- Pre-save docs: write design/task docs from i_context into the repo for downstream references ---
        try:
            i_ctx = getattr(act, "i_context", None)
            i_ctx_json = {}
            if isinstance(i_ctx, Document):
                # i_ctx.content is a JSON string
                i_ctx_json = json.loads(getattr(i_ctx, "content", "") or "{}")
            elif isinstance(i_ctx, dict):
                i_ctx_json = i_ctx
            dd = (i_ctx_json or {}).get("design_doc") or {}
            td = (i_ctx_json or {}).get("task_doc") or {}
            if dd.get("filename") is not None:
                await ctx.repo.docs.system_design.save(
                    filename=dd["filename"],
                    content=dd.get("content", ""),
                    dependencies=[]
                )
            if td.get("filename") is not None:
                await ctx.repo.docs.task.save(
                    filename=td["filename"],
                    content=td.get("content", ""),
                    dependencies=[]
                )
        except Exception as e:
            print(">> warn: pre-save docs failed:", e)
        # Bind required dependencies (inject only if present, to support different versions)
        for setter, value in [
            (getattr(act, "set_context", None), ctx),
            (getattr(act, "set_env", None), env),
            (getattr(act, "set_llm", None), llm),
        ]:
            if callable(setter) and value is not None:
                setter(value)
        if getattr(act, "context", None) is None and ctx is not None:
            try: act.context = ctx
            except Exception: pass
        if getattr(act, "rc", None) is None and getattr(eng, "rc", None) is not None:
            try: act.rc = eng.rc
            except Exception: pass
            
        # Fill config (WriteCode.run accesses self.config.inc)
        if getattr(act, "config", None) is None and getattr(ctx, "config", None) is not None:
            try: act.config = ctx.config
            except Exception:
                try: act.__dict__["config"] = ctx.config
                except Exception: pass
        # Support both Document and dict i_context shapes
        i_ctx = getattr(act, "i_context", None)
        if isinstance(i_ctx, Document):
            fname = getattr(i_ctx, "filename", "unknown")
        elif isinstance(i_ctx, dict):
            fname = i_ctx.get("filename", "unknown")
        else:
            fname = "unknown"
        print(f">> [manual] Run {i}/{len(actions)}: WriteCode -> {fname}")
        # Execute the action and obtain CodingContext
        coding_context = await act.run()

        # --- Persist src and update dependencies (key parts replicated from Engineer._act_sp_with_cr) ---
        try:
            deps = set()
            if getattr(coding_context, "design_doc", None):
                # Prefer root_relative_path; otherwise construct one
                ddoc = coding_context.design_doc
                deps.add(getattr(ddoc, "root_relative_path", None) or f"{ddoc.root_path}/{ddoc.filename}")
            if getattr(coding_context, "task_doc", None):
                tdoc = coding_context.task_doc
                deps.add(getattr(tdoc, "root_relative_path", None) or f"{tdoc.root_path}/{tdoc.filename}")
            if getattr(ctx.config, "inc", False) and getattr(coding_context, "code_plan_and_change_doc", None):
                cpc = coding_context.code_plan_and_change_doc
                deps.add(getattr(cpc, "root_relative_path", None) or f"{cpc.root_path}/{cpc.filename}")

            # WriteCode.run may rename the final filename to *_both.ext, so rely on code_doc.filename
            # TODO: Extract watermark code and source code from coding_context.code_doc.content
            detRes, code = extract_and_remove_tagContent("det_res", coding_context.code_doc.content)
            coding_context.code_doc.content = code

            p = Path(coding_context.filename)  # -> "SnakeGame.java"
            name = p.stem                 # -> "SnakeGame"
            ext  = p.suffix.lstrip('.')   # -> "java"
            fileName_wmDetRes = f"{name}_wm_detRes.txt"
            await act.repo.srcs.save(
                filename=coding_context.filename,
                dependencies=[d for d in deps if d],
                content=coding_context.code_doc.content,
            )
            await act.repo.srcs.save(
                # The watermark file does not participate in dependency management
                filename=fileName_wmDetRes,
                content=detRes,
            )
            print(f">> saved: src/{coding_context.filename}")
        except Exception as e:
            print(">> error: save src failed:", e)

async def codeGen(project_name: str, xargs:dict[str, Any]):
    PROJECT_PATH = Path(f"/home/zhaorz/project/CodeWM/MetaGPT/workspace/{project_name}").resolve()
    RECOVER_ROOT = Path("/home/zhaorz/project/CodeWM/MetaGPT/workspace/storage/team").resolve()
    PROJECT_HINT = project_name  # project prefix (adjust to your directory naming convention)
    
    # 1) Load the context using the same config you used when creating the snapshot
    local_vllm = Config.default() 
    local_vllm.update_via_cli(str(PROJECT_PATH), project_name=PROJECT_HINT, inc=False, reqa_file="", max_auto_summarize_code=0)
    ctx = Context(config=local_vllm)
    ctx.config.inc = False

    # 2) Point to a specific run's snapshot directory (not the root directory)
    RECOVER = RECOVER_ROOT
    print(">> recovering from:", RECOVER)

    # Do not rely on Team.deserialize's Engineer; use team.json as the source of truth for code_todos
    print(">> team.json exists:", (RECOVER / "team.json").exists(), "path:", RECOVER / "team.json")

    # --- Build a minimal usable Context.repo/git_repo/src_workspace ---
    PROJECT_PATH.mkdir(parents=True, exist_ok=True)
    # Convention for src_workspace: follow MetaGPT's workdir/name structure
    src_workspace = PROJECT_PATH / PROJECT_PATH.name
    src_workspace.mkdir(parents=True, exist_ok=True)
    docs_sd = PROJECT_PATH / "docs/system_design"; docs_sd.mkdir(parents=True, exist_ok=True)
    docs_task = PROJECT_PATH / "docs/task"; docs_task.mkdir(parents=True, exist_ok=True)
    resources_dir = PROJECT_PATH / "resources"; resources_dir.mkdir(parents=True, exist_ok=True)

    try:
        git_repo = GitRepository(str(PROJECT_PATH))
    except TypeError:
        git_repo = GitRepository(workdir=str(PROJECT_PATH))
    ctx.git_repo = git_repo
    ctx.repo = ProjectRepo(git_repo)
    ctx.src_workspace = src_workspace
    print(">> ctx.git_repo.workdir =", getattr(ctx.git_repo, "workdir", None))

    # --- Read code_todos from team.json (treat it as the authoritative source) ---
    team_json = RECOVER / "team.json"
    with team_json.open("r", encoding="utf-8") as f:
        team_obj = json.load(f)
    roles_obj = ((team_obj or {}).get("env") or {}).get("roles") or {}
    eng_obj = roles_obj.get("Engineer") or roles_obj.get("engineer") or {}
    code_todos_raw = list(eng_obj.get("code_todos") or [])
    if not code_todos_raw:
        raise RuntimeError("Engineer.code_todos in team.json is empty; cannot proceed.")

    # --- Build a lightweight company stub just to satisfy _run_actions_manually signature ---
    company_stub = SimpleNamespace(context=ctx, env=None)
    
    # 3) Create a "clean" Engineer and bind LLM/Context (no deserialization)
    eng = Engineer(config=local_vllm)
    eng.config = ctx.config
    eng.context = ctx
    eng.llm.config.__dict__["xargs"] = xargs
    # Additionally ensure incremental mode is disabled at the role level
    # try: eng.config.inc = False
    # except Exception: pass

    # 4) Switch Engineer to BY_ORDER and inject the actions via set_actions
    # If deserialized code_todos is empty: backfill from RECOVER/team.json; if still empty, try rebuilding from docs/*
    code_todos = code_todos_raw  # directly use the snapshot's todo list
    
    try:
        from metagpt.const import ReActMode
        eng._set_react_mode(ReActMode.BY_ORDER)
    except Exception:
        eng._set_react_mode(react_mode="by_order")

    # Instantiate WriteCode actions explicitly from code_todos and inject (with i_context/prefix/desc)
    actions = []
    for td in code_todos:
        if td is None:
            continue
        if not isinstance(td, dict):
            continue
        # Reconstruct i_context as schema.Document (more robust than raw dict)
        i_ctx_dict = td.get("i_context") or {}
        doc = Document(**i_ctx_dict)
        act = WriteCode(i_context=doc, context=ctx, llm=eng.llm)
        # Sync prefix/desc (optional)
        if "prefix" in td: setattr(act, "prefix", td.get("prefix", ""))
        if "desc" in td:   setattr(act, "desc", td.get("desc", ""))
        actions.append(act)
    if not actions:
        raise RuntimeError("Engineer.code_todos is empty or malformed; cannot build WriteCode actions.")
    # Optional: only for logging; does not depend on Team scheduling
    try:
        eng.set_actions(actions)
        setattr(eng, "enabled", True)
    except Exception:
        pass

    # Explicitly reset the run pointer to the start of actions
    # (field names vary across versions; set what we can)
    if hasattr(eng, "rc"):
        try:
            # Reset several common field names
            for k, v in [
                ("cur_action_idx", 0),
                ("state", 0),                # -1(not started) -> 0(ready to run)
                ("reacted_cnt", 0),
                ("cur_action", None),
            ]:
                if hasattr(eng.rc, k):
                    setattr(eng.rc, k, v)
        except Exception:
            pass

    # 5) Inspect the current breakpoint
    code_todos = code_todos or []
    print("eng.code_todos:", [
        (td.get("i_context", {}) if isinstance(td, dict) else {}).get("filename")
        for td in code_todos
    ])
    print(">> ready, ctx.git_repo.workdir =", getattr(getattr(ctx, "git_repo", None), "workdir", None))
    
    # 6) Do not depend on Team scheduling; execute each action manually (most robust)
    await _run_actions_manually(
        # Pass our minimal company_stub (only .context / .env are needed)
        company_stub,
        eng,
        actions
    )
    print(">> [manual] all WriteCode actions finished.")

if __name__ == "__main__":
    project_name = "brick_breaker_game"
    xargs = {
        "temperature": 0.7,
        "max_tokens": 4096,
        # "rng_seed": make_seed(32),
        "rng_seed": 3107160669,
        "internal_processor_names": [],
        "external_processor_names": [],
        "external_processor_params": {
            "sweet": {"gamma": 0.25, "delta": 0, "entropy_threshold": 0.85},
            "wllm": {"gamma": 0.25, "delta": 1},
        },
    }
    asyncio.run(codeGen(project_name, xargs))
