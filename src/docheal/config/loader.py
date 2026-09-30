from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field

from docheal.errors import ConfigurationError
from docheal.models.common import StrictModel


class SourceConfig(StrictModel):
    include: list[str] = Field(default_factory=lambda: ["src"])
    exclude: list[str] = Field(default_factory=lambda: ["tests", ".venv", "venv"])
    language: str = "python"


class DocumentationConfig(StrictModel):
    include: list[str] = Field(default_factory=lambda: ["docs", "README.md"])


class EmbeddingConfig(StrictModel):
    model: str = "text-embedding-3-small"
    similarity_threshold: float = Field(default=0.80, ge=0, le=1)
    collection: str = "docheal"


class LLMConfig(StrictModel):
    model: str = "gpt-4.1-mini"
    temperature: float = Field(default=0, ge=0, le=2)
    timeout_seconds: int = Field(default=60, ge=1)


class DecisionConfig(StrictModel):
    auto_fix_threshold: float = Field(default=0.90, ge=0, le=1)
    human_review_threshold: float = Field(default=0.70, ge=0, le=1)


class GitHubConfig(StrictModel):
    auto_fix_enabled: bool = False
    branch_prefix: str = "docheal/fix"


class IndexConfig(StrictModel):
    path: str = ".docheal/index.json"
    chroma_path: str = ".docheal/chroma"


class AppConfig(StrictModel):
    source: SourceConfig = Field(default_factory=SourceConfig)
    documentation: DocumentationConfig = Field(default_factory=DocumentationConfig)
    embeddings: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    decision: DecisionConfig = Field(default_factory=DecisionConfig)
    github: GitHubConfig = Field(default_factory=GitHubConfig)
    index: IndexConfig = Field(default_factory=IndexConfig)


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: str | Path | None = None) -> AppConfig:
    data: dict[str, Any] = {}
    if path:
        config_path = Path(path)
        if not config_path.is_file():
            raise ConfigurationError(f"configuration file not found: {config_path}")
        try:
            data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise ConfigurationError(f"cannot load configuration: {exc}") from exc
    env: dict[str, Any] = {}
    if model := os.getenv("DOCHEAL_LLM_MODEL"):
        env.setdefault("llm", {})["model"] = model
    if model := os.getenv("DOCHEAL_EMBEDDING_MODEL"):
        env.setdefault("embeddings", {})["model"] = model
    if threshold := os.getenv("DOCHEAL_AUTO_FIX_THRESHOLD"):
        env.setdefault("decision", {})["auto_fix_threshold"] = float(threshold)
    if value := os.getenv("DOCHEAL_AUTO_FIX_ENABLED"):
        env.setdefault("github", {})["auto_fix_enabled"] = value.lower() in {"1", "true", "yes"}
    try:
        config = AppConfig.model_validate(_merge(data, env))
    except (ValueError, TypeError) as exc:
        raise ConfigurationError(f"invalid configuration: {exc}") from exc
    if config.decision.human_review_threshold > config.decision.auto_fix_threshold:
        raise ConfigurationError("human-review threshold cannot exceed auto-fix threshold")
    return config

