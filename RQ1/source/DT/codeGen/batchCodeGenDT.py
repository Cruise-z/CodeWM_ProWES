"""Compatibility entry point for batch code generation.

The implementation is split into focused modules. Importing from this file keeps
old call sites working, and executing it runs the default manual batch config.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from decimal import Decimal
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, List, Literal, Optional, Union

from batch_environment import configure_default_proxy

configure_default_proxy()

from agentCodeGen import codeGen, make_seed
from aiAPI import *
from batch_docker import docker_exec
from batch_file_ops import find_path, shellDelete, shellPaste
from batch_processors import (
    _is_no_external_processor,
    _iteration_rng_seed,
    _processor_name,
    _require_lang,
    build_external_processor_config,
    build_external_processor_params,
    build_result_dir,
)
from batch_runner import codeGenBatch, filterPrompt, selectRngSeed
from batch_snapshots import (
    calculate_diversity_metrics,
    describe_snapshot_diff,
    get_postfix,
    get_programming_language,
    hash_code_snapshot,
    remove_leading_h2_line,
    snapshot_code_files,
    strength_values,
)
from batch_utils import (
    MAX_RESULT_DIR_COMPONENT_BYTES,
    _arg_value,
    _as_bool,
    _merge_nested_config,
    _nonempty,
    _shorten_path_component,
    _utf8_prefix,
    _utf8_suffix,
    read_file,
)


if __name__ == "__main__":
    from batch_run_config import run_default_batch

    if len(sys.argv) > 2:
        raise SystemExit("Usage: python batchCodeGenDT.py [batch_run_config.json]")
    run_default_batch(sys.argv[1] if len(sys.argv) == 2 else None)
