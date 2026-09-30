from __future__ import annotations

import hashlib
import re
from pathlib import Path, PurePosixPath

from docheal.errors import ParserError
from docheal.models import DocumentationSection

HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
CODE_REF = re.compile(r"`([A-Za-z_][\w.]*(?:\([^`]*\))?)`|\b([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+)\b")


def _section_id(file_path: str, heading_path: list[str], ordinal: int) -> str:
    slug = "/".join(re.sub(r"[^a-z0-9]+", "-", item.lower()).strip("-") for item in heading_path)
    return f"{PurePosixPath(file_path).as_posix()}#{slug or 'preamble'}:{ordinal}"


class MarkdownParser:
    def parse_file(self, path: Path, repository_root: Path | None = None) -> list[DocumentationSection]:
        root = (repository_root or path.parent).resolve()
        resolved = path.resolve()
        try:
            relative = resolved.relative_to(root).as_posix()
            source = resolved.read_text(encoding="utf-8")
        except (OSError, ValueError) as exc:
            raise ParserError(f"cannot read Markdown {path}: {exc}") from exc
        return self.parse_text(source, relative)

    def parse_text(self, source: str, file_path: str) -> list[DocumentationSection]:
        lines = source.splitlines(keepends=True)
        headings: list[tuple[int, int, str]] = []
        in_fence = False
        for index, line in enumerate(lines, 1):
            if line.lstrip().startswith(("```", "~~~")):
                in_fence = not in_fence
            if not in_fence and (match := HEADING.match(line.rstrip("\r\n"))):
                headings.append((index, len(match.group(1)), match.group(2).strip()))
        if not headings and source.strip():
            headings = [(1, 1, PurePosixPath(file_path).stem)]
        sections: list[DocumentationSection] = []
        stack: list[tuple[int, str, str]] = []
        for ordinal, (start, level, title) in enumerate(headings):
            end = (headings[ordinal + 1][0] - 1) if ordinal + 1 < len(headings) else max(1, len(lines))
            while stack and stack[-1][0] >= level:
                stack.pop()
            path_titles = [item[1] for item in stack] + [title]
            section_id = _section_id(file_path, path_titles, ordinal)
            parent_id = stack[-1][2] if stack else None
            content = "".join(lines[start - 1 : end]).rstrip("\r\n")
            refs: set[str] = set()
            for match in CODE_REF.finditer(content):
                reference = match.group(1) or match.group(2)
                refs.add(reference.split("(", 1)[0])
            sections.append(
                DocumentationSection(
                    id=section_id,
                    file_path=PurePosixPath(file_path).as_posix(),
                    heading=title,
                    heading_path=path_titles,
                    content=content,
                    start_line=start,
                    end_line=end,
                    referenced_symbols=sorted(refs),
                    parent_id=parent_id,
                    metadata={"level": level, "content_hash": hashlib.sha256(content.encode()).hexdigest()},
                )
            )
            stack.append((level, title, section_id))
        return sections

