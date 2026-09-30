from __future__ import annotations

import json
import os
from typing import Any, Protocol

import httpx

from docheal.errors import LLMError


class LLMProvider(Protocol):
    def complete_json(self, system: str, user: str, schema_name: str, schema: dict[str, Any]) -> dict[str, Any]: ...


class OpenAIProvider:
    """Small structured-output client with no provider types leaking into business logic."""

    def __init__(self, model: str, api_key: str | None = None, timeout: float = 60) -> None:
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.timeout = timeout
        self.last_usage: dict[str, int] = {}
        self.usage: dict[str, int] = {}

    def complete_json(self, system: str, user: str, schema_name: str, schema: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise LLMError("OPENAI_API_KEY is required for LLM analysis")
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {"type": "json_schema", "json_schema": {"name": schema_name, "strict": True, "schema": schema}},
        }
        try:
            response = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
            self.last_usage = {
                key: int(value) for key, value in payload.get("usage", {}).items() if isinstance(value, int)
            }
            for key, value in self.last_usage.items():
                self.usage[key] = self.usage.get(key, 0) + value
            return json.loads(content)
        except (httpx.HTTPError, KeyError, IndexError, json.JSONDecodeError, TypeError) as exc:
            raise LLMError(f"structured LLM request failed: {exc}") from exc
