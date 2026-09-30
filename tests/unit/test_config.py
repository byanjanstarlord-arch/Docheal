from pathlib import Path

import pytest

from docheal.config import load_config
from docheal.errors import ConfigurationError


def test_environment_override(monkeypatch, tmp_path: Path):
    config = tmp_path / "config.yaml"
    config.write_text("llm:\n  model: base\n", encoding="utf-8")
    monkeypatch.setenv("DOCHEAL_LLM_MODEL", "override")
    assert load_config(config).llm.model == "override"


def test_invalid_threshold_order(tmp_path: Path):
    config = tmp_path / "config.yaml"
    config.write_text("decision:\n  auto_fix_threshold: 0.5\n  human_review_threshold: 0.8\n", encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_config(config)

