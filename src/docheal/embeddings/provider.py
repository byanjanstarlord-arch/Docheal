from __future__ import annotations

import os
from typing import Protocol

import httpx

from docheal.errors import EmbeddingError


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class OpenAIEmbeddingProvider:
    def __init__(self, model: str = "text-embedding-3-small", api_key: str | None = None, timeout: float = 60) -> None:
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.timeout = timeout
        self.last_usage: dict[str, int] = {}
        self.usage: dict[str, int] = {}

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key:
            raise EmbeddingError("OPENAI_API_KEY is required for semantic indexing")
        try:
            response = httpx.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "input": texts},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            rows = sorted(payload["data"], key=lambda item: item["index"])
            self.last_usage = {
                key: int(value) for key, value in payload.get("usage", {}).items() if isinstance(value, int)
            }
            for key, value in self.last_usage.items():
                self.usage[key] = self.usage.get(key, 0) + value
            return [row["embedding"] for row in rows]
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise EmbeddingError(f"embedding request failed: {exc}") from exc
