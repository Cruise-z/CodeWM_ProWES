from __future__ import annotations
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


class LLMProvider:
    def chat(self, messages: List[Dict[str, str]], *, temperature: float = 0.0,
             seed: Optional[int] = None,
             max_completion_tokens: Optional[int] = None,
             reasoning_effort: Optional[str] = None) -> str:
        raise NotImplementedError


@dataclass
class OpenAICompatibleProvider(LLMProvider):
    base_url: str
    model: str
    api_key_env: str = "OPENAI_API_KEY"
    timeout: int = 120

    def chat(self, messages, *, temperature=0.0, seed=None, max_completion_tokens=None,
             reasoning_effort=None) -> str:
        key = os.environ.get(self.api_key_env)
        if not key:
            raise RuntimeError(f"Environment variable {self.api_key_env} is not set")
        url = self.base_url.rstrip("/") + "/chat/completions"
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if seed is not None:
            payload["seed"] = int(seed)
        if max_completion_tokens is not None:
            payload["max_completion_tokens"] = int(max_completion_tokens)
        if reasoning_effort is not None:
            payload["reasoning_effort"] = reasoning_effort
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "User-Agent": "RQ2-CodeWM-Experiment/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                request_id = resp.headers.get("x-request-id")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:2000]
            raise RuntimeError(f"LLM endpoint returned HTTP {exc.code}: {detail}") from exc
        choice = body["choices"][0]
        content = choice["message"].get("content") or ""
        self.last_response_meta = {
            "response_id": body.get("id"),
            "response_model": body.get("model"),
            "system_fingerprint": body.get("system_fingerprint"),
            "request_id": request_id,
            "usage": body.get("usage"),
            "finish_reason": choice.get("finish_reason"),
            "content_characters": len(content),
        }
        return content


@dataclass
class LegacyAiAPIProvider(LLMProvider):
    config_path: str
    profile: str
    model_attr: str = "gpt4"

    def __post_init__(self):
        from aiAPI import Client, Model, common_chat
        self._Client = Client
        self._Model = Model
        self._common_chat = common_chat
        self.client = Client(self.config_path, self.profile)

    def chat(self, messages, *, temperature=0.0, seed=None, max_completion_tokens=None,
             reasoning_effort=None) -> str:
        # The legacy wrapper accepts a list of textual messages. We pre-build RAG context,
        # so no file_chat/retrieval call is needed here.
        model = getattr(self._Model, self.model_attr)
        flattened = []
        for m in messages:
            flattened.append(f"[{m['role'].upper()}]\n{m['content']}")
        return self._common_chat(self.client, model, flattened, StreamMode=False,
                                 cache_tag="rq2_rule_rag")


class MockIdentityProvider(LLMProvider):
    """Offline test provider: echoes the fenced source code unchanged."""
    def chat(self, messages, *, temperature=0.0, seed=None, max_completion_tokens=None,
             reasoning_effort=None) -> str:
        import re
        text = messages[-1]["content"]
        m = re.search(r"```([A-Za-z0-9_+-]+)\n(.*?)\n```", text, flags=re.S)
        code = m.group(2) if m else ""
        lang = m.group(1) if m else "text"
        return f"<applied_rules>NONE</applied_rules>\n```{lang}\n{code}\n```"
