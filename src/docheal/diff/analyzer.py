from __future__ import annotations

import ast
import re
import textwrap

from docheal.models import ChangedEntity, ChangedFile, CodeEntity

DIFF_HEADER = re.compile(r"^diff --git a/(.+) b/(.+)$")
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


class DiffAnalyzer:
    def parse_unified_diff(self, diff: str) -> list[ChangedFile]:
        files: list[ChangedFile] = []
        current: dict | None = None
        old_line = new_line = 0
        for line in diff.splitlines():
            header = DIFF_HEADER.match(line)
            if header:
                if current:
                    files.append(ChangedFile(**current))
                current = {
                    "old_path": header.group(1), "new_path": header.group(2), "change_type": "modified",
                    "added_lines": [], "removed_lines": [], "patch": "",
                }
                continue
            if current is None:
                continue
            current["patch"] += line + "\n"
            if line.startswith("new file mode"):
                current["change_type"] = "added"
            elif line.startswith("deleted file mode"):
                current["change_type"] = "deleted"
            elif line.startswith("rename from "):
                current["old_path"] = line.removeprefix("rename from ")
                current["change_type"] = "renamed"
            elif line.startswith("rename to "):
                current["new_path"] = line.removeprefix("rename to ")
            elif match := HUNK.match(line):
                old_line, new_line = int(match.group(1)), int(match.group(3))
            elif line.startswith("+") and not line.startswith("+++"):
                current["added_lines"].append(new_line)
                new_line += 1
            elif line.startswith("-") and not line.startswith("---"):
                current["removed_lines"].append(old_line)
                old_line += 1
            elif not line.startswith("\\"):
                old_line += 1
                new_line += 1
        if current:
            files.append(ChangedFile(**current))
        return files

    def compare_entities(
        self, old_entities: list[CodeEntity], new_entities: list[CodeEntity]
    ) -> list[ChangedEntity]:
        old = {item.id: item for item in old_entities}
        new = {item.id: item for item in new_entities}
        changes: list[ChangedEntity] = []
        for entity_id in sorted(old.keys() | new.keys()):
            before, after = old.get(entity_id), new.get(entity_id)
            if before is None and after is not None:
                changes.append(ChangedEntity(entity_id=entity_id, new_source=after.source_code, change_type="added", changed_lines=list(range(after.start_line, after.end_line + 1)), significance=0.82, reason="public code entity added"))
            elif after is None and before is not None:
                changes.append(ChangedEntity(entity_id=entity_id, old_source=before.source_code, change_type="removed", changed_lines=list(range(before.start_line, before.end_line + 1)), significance=0.95, reason="documented code entity removed"))
            elif before and after and before.source_code != after.source_code:
                if self._ast_equivalent(before.source_code, after.source_code):
                    continue
                signature_changed = before.signature != after.signature
                changes.append(ChangedEntity(
                    entity_id=entity_id,
                    old_source=before.source_code,
                    new_source=after.source_code,
                    change_type="signature_changed" if signature_changed else "modified",
                    changed_lines=self._changed_lines(before.source_code, after.source_code, after.start_line),
                    significance=0.98 if signature_changed else 0.78,
                    reason="call signature changed" if signature_changed else "entity behavior may have changed",
                ))
        return changes

    @staticmethod
    def _ast_equivalent(left: str, right: str) -> bool:
        try:
            return ast.dump(ast.parse(textwrap.dedent(left)), include_attributes=False) == ast.dump(ast.parse(textwrap.dedent(right)), include_attributes=False)
        except SyntaxError:
            return False

    @staticmethod
    def _changed_lines(left: str, right: str, offset: int) -> list[int]:
        import difflib

        changed: set[int] = set()
        matcher = difflib.SequenceMatcher(a=left.splitlines(), b=right.splitlines())
        for tag, _i1, _i2, j1, j2 in matcher.get_opcodes():
            if tag != "equal":
                changed.update(range(offset + j1, offset + max(j1 + 1, j2)))
        return sorted(changed)

