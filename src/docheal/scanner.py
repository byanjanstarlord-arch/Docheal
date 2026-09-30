from __future__ import annotations

from pathlib import Path

from docheal.config import AppConfig
from docheal.models import CodeEntity, DocumentationSection
from docheal.parser import MarkdownParser, PythonParser


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


class RepositoryScanner:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.python = PythonParser()
        self.markdown = MarkdownParser()

    def scan(self, repository: Path) -> tuple[list[CodeEntity], list[DocumentationSection]]:
        root = repository.resolve()
        code_files: set[Path] = set()
        doc_files: set[Path] = set()
        for entry in self.config.source.include:
            candidate = (root / entry).resolve()
            if not _inside(candidate, root) or not candidate.exists():
                continue
            code_files.update(candidate.rglob("*.py") if candidate.is_dir() else ([candidate] if candidate.suffix == ".py" else []))
        excluded = {part for value in self.config.source.exclude for part in Path(value).parts}
        code_files = {path for path in code_files if not excluded.intersection(path.relative_to(root).parts)}
        for entry in self.config.documentation.include:
            candidate = (root / entry).resolve()
            if not _inside(candidate, root) or not candidate.exists():
                continue
            doc_files.update(candidate.rglob("*.md") if candidate.is_dir() else ([candidate] if candidate.suffix.lower() == ".md" else []))
        code = [entity for path in sorted(code_files) for entity in self.python.parse_file(path, root)]
        docs = [section for path in sorted(doc_files) for section in self.markdown.parse_file(path, root)]
        return code, docs

