"""Docker/build execution helper for generated projects."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from batch_snapshots import describe_snapshot_diff, remove_leading_h2_line, snapshot_code_files

def docker_exec(
    prev_code_snapshot: Optional[dict[str, str]],
    codeFilePath: Path,
    testFilePath: Path,
    LANG: str,
    desc: str,
    *,
    prepared_code_snapshot: Optional[dict[str, str]] = None,
) -> tuple[dict[str, str], int, bool]:
    """
    Clean generated source files, compare them with the previous source snapshot,
    and run docker tests only when the source code changed.

    Returns
    -------
    tuple[dict[str, str], int, bool]
        curr_code_snapshot, retCode, skipped
    """
    retCode = -1
    skipped = False
    curr_code_snapshot: dict[str, str] = {}

    try:
        if prepared_code_snapshot is None:
            remove_leading_h2_line(codeFilePath)
            curr_code_snapshot = snapshot_code_files(codeFilePath, LANG)
        else:
            curr_code_snapshot = prepared_code_snapshot

        if prev_code_snapshot is None:
            print(f"{desc} no previous code snapshot, skipping docker test")
            retCode = 0
            skipped = True
        else:
            if curr_code_snapshot == prev_code_snapshot:
                print(f"{desc} code unchanged, skipping docker test")
                retCode = 0
                skipped = True
            else:
                diff_summary = describe_snapshot_diff(prev_code_snapshot, curr_code_snapshot)
                print(f"{desc} code changed, running test: {diff_summary}")

                res = subprocess.run(
                    ["bash", testFilePath, codeFilePath],
                    env={
                        **os.environ,

                        # Maven proxy
                        "ENABLE_MAVEN_PROXY_CONFIG": "1",
                        "MAVEN_PROXY_HOST": "192.168.129.183",
                        "MAVEN_PROXY_PORT": "7897",

                        # Test timeout
                        "TEST_TIME_LIMIT": "30",

                        # Runtime check
                        "RUN_CHECK_SECONDS": "5",
                        "RUN_CHECK_KILL_AFTER": "2",

                        # Runtime output-loop detection
                        "RUNTIME_MAX_OUTPUT_BYTES": "262144",
                        "RUNTIME_MAX_OUTPUT_LINES": "200",
                        "RUNTIME_MAX_SAME_LINE": "30",
                        "RUNTIME_MAX_CONSECUTIVE_SAME_LINE": "10",

                        # Optional CPU busy-loop detection
                        "RUNTIME_ENABLE_CPU_BUSY_CHECK": "1",
                        "RUNTIME_CPU_BUSY_THRESHOLD": "95",
                        "RUNTIME_CPU_BUSY_MIN_SAMPLES": "6",
                    },
                    check=False,
                    text=True,
                    capture_output=True,
                )
                if res.stdout:
                    print(res.stdout)
                if res.stderr:
                    print(res.stderr, file=sys.stderr)
                retCode = res.returncode

    except Exception as e:
        print(e)

    return curr_code_snapshot, retCode, skipped
