from __future__ import annotations

import re

from docheal.mapping.graph import RepositoryIndex
from docheal.models import ChangedEntity, CodeDocLink, DocumentationSection


class AffectedDocumentationResolver:
    def resolve(
        self, changes: list[ChangedEntity], index: RepositoryIndex, limit_per_entity: int = 5
    ) -> dict[str, list[tuple[DocumentationSection, CodeDocLink]]]:
        result: dict[str, list[tuple[DocumentationSection, CodeDocLink]]] = {}
        for change in changes:
            if change.significance < 0.5:
                continue
            seen: set[str] = set()
            matches: list[tuple[DocumentationSection, CodeDocLink]] = []
            for section, link in index.sections_for(change.entity_id):
                if section.id not in seen:
                    seen.add(section.id)
                    matches.append((section, link))
                if len(matches) >= limit_per_entity:
                    break
            # Removed entities are absent from a current-tree index. Retain deterministic
            # value by resolving their stable symbol directly against current docs.
            if not matches and change.change_type == "removed":
                qualified = change.entity_id.split("::", 1)[-1]
                symbol = qualified.rsplit(".", 1)[-1]
                for section in index.documentation_sections:
                    if symbol in section.referenced_symbols or re.search(rf"(?<![\w]){re.escape(symbol)}(?![\w])", section.content):
                        link = CodeDocLink(
                            code_entity_id=change.entity_id,
                            documentation_section_id=section.id,
                            link_type="symbol",
                            similarity_score=0.9,
                            source="deterministic",
                            confidence=0.9,
                        )
                        matches.append((section, link))
                        if len(matches) >= limit_per_entity:
                            break
            if matches:
                result[change.entity_id] = matches
        return result
