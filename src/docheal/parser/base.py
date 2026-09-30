from pathlib import Path
from typing import Generic, Protocol, TypeVar

T = TypeVar("T")


class Parser(Protocol, Generic[T]):
    def parse_text(self, source: str, file_path: str) -> list[T]: ...

    def parse_file(self, path: Path, repository_root: Path | None = None) -> list[T]: ...

