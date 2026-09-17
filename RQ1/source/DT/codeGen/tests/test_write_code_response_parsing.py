from __future__ import annotations

from metagpt.actions.write_code import _parse_code_response, _split_detection_result
from metagpt.provider.base_llm import BaseLLM


def test_parse_complete_fenced_code() -> None:
    response = "## Code: Main.java\n```java\nclass Main {}\n```\nDone."

    assert _parse_code_response(response) == "class Main {}\n"


def test_parse_truncated_fenced_code_without_backtracking() -> None:
    code = "class Main {\n" + ("    int value = 1;\n" * 20_000)
    response = f"## Code: Main.java\n```java\n{code}"

    assert _parse_code_response(response) == code


def test_parse_unfenced_response_preserves_original_text() -> None:
    response = "class Main {}"

    assert _parse_code_response(response) == response


def test_detection_result_is_removed_before_truncated_code_parsing() -> None:
    response = (
        "```java\nclass Main {\n"
        '<det_res>{"score": 1.25}</det_res>'
    )

    generated_text, detection_result = _split_detection_result(response)

    assert generated_text == "```java\nclass Main {\n"
    assert detection_result == '<det_res>{"score": 1.25}</det_res>'
    assert _parse_code_response(generated_text) == "class Main {\n"


def test_length_finish_reason_preserves_content_and_detection_payload() -> None:
    response = {
        "choices": [
            {
                "message": {"content": "```java\nclass Main {\n"},
                "finish_reason": "length",
                "wm_detection": {"score": 1.25},
            }
        ],
        "usage": {"completion_tokens": 4096},
    }

    holder = type("CompletionMetadataHolder", (), {})()
    result = BaseLLM.get_choice_text_local(holder, response, 0)

    assert result == "```java\nclass Main {\n\n<det_res>\n{'score': 1.25}\n</det_res>"
    assert holder.last_local_completion_metadata == {
        "choice_index": 0,
        "finish_reason": "length",
        "usage": {"completion_tokens": 4096},
        "response_id": None,
        "model": None,
        "content_character_count": 21,
    }
