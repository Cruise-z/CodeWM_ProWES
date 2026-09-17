import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from run_llm_full_1000 import load_env_file, summarize_output


def test_load_env_file_supports_markdown_url_and_shell_key(tmp_path):
    path = tmp_path / "llm.env"
    path.write_text(
        "base_url: [https://example.invalid/v1](https://example.invalid/v1)\n"
        "OPENAI_API_KEY=dummy-key\n",
        encoding="utf-8",
    )
    key, base_url = load_env_file(path)
    assert key == "dummy-key"
    assert base_url == "https://example.invalid/v1"


def test_summarize_output_accounts_status_and_usage(tmp_path):
    path = tmp_path / "result.jsonl"
    rows = [
        {
            "attack_meta": {
                "status": "valid_attack",
                "changed": True,
                "syntax_valid": True,
                "provider_response": {
                    "response_model": "model-snapshot",
                    "usage": {
                        "prompt_tokens": 100,
                        "completion_tokens": 20,
                        "completion_tokens_details": {"reasoning_tokens": 0},
                    },
                },
            }
        },
        {
            "attack_meta": {
                "status": "no_op",
                "changed": False,
                "syntax_valid": True,
                "provider_response": {
                    "response_model": "model-snapshot",
                    "usage": {"prompt_tokens": 80, "completion_tokens": 10},
                },
            }
        },
    ]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    summary = summarize_output(path)
    assert summary["rows"] == 2
    assert summary["status_counts"] == {"valid_attack": 1, "no_op": 1}
    assert summary["prompt_tokens"] == 180
    assert summary["completion_tokens"] == 30
    assert summary["response_models"] == ["model-snapshot"]
