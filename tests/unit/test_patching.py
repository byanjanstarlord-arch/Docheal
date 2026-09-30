from pathlib import Path

import pytest

from docheal.errors import PatchError
from docheal.models import RepairProposal
from docheal.repair import DocumentationPatcher


def proposal(path="docs/api.md"):
    return RepairProposal(file_path=path, section_id="id", original_content="## f\n`f(x)` works.", corrected_content="## f\n`f(x, y)` works.", explanation="signature", confidence=.95)


def test_precise_markdown_patch(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    target = docs / "api.md"
    target.write_text("# API\n\n## f\n`f(x)` works.\n\n## g\nkeep\n", encoding="utf-8")
    DocumentationPatcher().apply(tmp_path, proposal())
    updated = target.read_text(encoding="utf-8")
    assert "`f(x, y)`" in updated
    assert "## g\nkeep" in updated


def test_rejects_path_traversal(tmp_path: Path):
    with pytest.raises(PatchError):
        DocumentationPatcher().apply(tmp_path, proposal("../outside.md"))


def test_fails_if_original_changed(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "api.md").write_text("# different", encoding="utf-8")
    with pytest.raises(PatchError):
        DocumentationPatcher().apply(tmp_path, proposal())

