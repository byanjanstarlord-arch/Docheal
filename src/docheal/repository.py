from __future__ import annotations

import subprocess
from pathlib import Path

from docheal.errors import DocHealError


class GitRepository:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _run(self, *args: str, check: bool = True) -> str:
        process = subprocess.run(
            ["git", *args], cwd=self.root, text=True, encoding="utf-8", errors="replace",
            capture_output=True, check=False,
        )
        if check and process.returncode:
            raise DocHealError(f"git {' '.join(args[:2])} failed: {process.stderr.strip()}")
        return process.stdout

    def diff(self, base: str, head: str = "HEAD") -> str:
        return self._run("diff", "--no-ext-diff", "--unified=3", base, head, "--", "*.py")

    def show(self, ref: str, path: str) -> str | None:
        process = subprocess.run(
            ["git", "show", f"{ref}:{path}"], cwd=self.root, text=True, encoding="utf-8",
            errors="replace", capture_output=True, check=False,
        )
        return process.stdout if process.returncode == 0 else None

    def current_text(self, path: str) -> str | None:
        target = (self.root / path).resolve()
        try:
            target.relative_to(self.root)
        except ValueError:
            return None
        return target.read_text(encoding="utf-8") if target.is_file() else None

