from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from docheal.errors import PatchError
from docheal.models import RepairProposal
from docheal.parser import MarkdownParser


class DocumentationPatcher:
    ALLOWED_SUFFIXES: ClassVar[set[str]] = {".md", ".markdown"}

    def apply(self, repository: Path, proposal: RepairProposal) -> Path:
        root = repository.resolve()
        target = (root / proposal.file_path).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise PatchError("repair target escapes repository root") from exc
        if target.suffix.lower() not in self.ALLOWED_SUFFIXES:
            raise PatchError("repairs are restricted to Markdown files")
        if not target.is_file():
            raise PatchError(f"documentation target does not exist: {proposal.file_path}")
        raw = target.read_bytes()
        newline = "\r\n" if b"\r\n" in raw else "\n"
        text = raw.decode("utf-8")
        original = proposal.original_content.replace("\r\n", "\n").replace("\n", newline)
        occurrences = text.count(original)
        if occurrences != 1:
            raise PatchError(f"expected original section exactly once, found {occurrences}")
        corrected = proposal.corrected_content.replace("\r\n", "\n").replace("\n", newline)
        updated = text.replace(original, corrected, 1)
        try:
            MarkdownParser().parse_text(updated, proposal.file_path)
        except Exception as exc:
            raise PatchError(f"patched Markdown failed structural parsing: {exc}") from exc
        temporary = target.with_suffix(target.suffix + ".docheal.tmp")
        temporary.write_text(updated, encoding="utf-8", newline="")
        temporary.replace(target)
        return target
