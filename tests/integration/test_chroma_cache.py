import importlib.util
from pathlib import Path

import pytest

from docheal.config import AppConfig
from docheal.pipeline import build_index

pytestmark = pytest.mark.skipif(importlib.util.find_spec("chromadb") is None, reason="ChromaDB optional runtime is not installed")


class CountingEmbeddings:
    def __init__(self):
        self.requests = 0

    def embed(self, texts):
        self.requests += len(texts)
        return [[float(index + 1), 1.0] for index, _text in enumerate(texts)]


def test_unchanged_content_reuses_chroma_vectors(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "src" / "api.py").write_text("def lookup(user_id):\n    return user_id\n", encoding="utf-8")
    (tmp_path / "docs" / "api.md").write_text("# lookup\nUse `lookup(user_id)`.\n", encoding="utf-8")
    config = AppConfig()
    provider = CountingEmbeddings()
    build_index(tmp_path, config, provider)
    first_requests = provider.requests
    build_index(tmp_path, config, provider)
    assert first_requests == 2
    assert provider.requests == first_requests
