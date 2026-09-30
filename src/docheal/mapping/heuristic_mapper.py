from __future__ import annotations

import re

from docheal.models import CodeDocLink, CodeEntity, DocumentationSection


class HeuristicMapper:
    def map(
        self, entities: list[CodeEntity], sections: list[DocumentationSection]
    ) -> list[CodeDocLink]:
        links: dict[tuple[str, str], CodeDocLink] = {}
        for entity in entities:
            names = {entity.symbol_name, entity.qualified_name}
            route = entity.metadata.get("route_or_command")
            if isinstance(route, str):
                names.add(route)
            for section in sections:
                exact_ref = bool(names.intersection(section.referenced_symbols))
                direct_text = any(
                    re.search(rf"(?<![\w]){re.escape(name)}(?![\w])", section.content)
                    for name in names
                )
                heading_match = entity.symbol_name.lower() in section.heading.lower()
                if not (exact_ref or direct_text or heading_match):
                    continue
                if exact_ref:
                    link_type, score = "qualified_name" if entity.qualified_name in section.referenced_symbols else "symbol", 1.0
                elif route and route in section.content:
                    link_type, score = ("route" if entity.entity_type == "endpoint" else "cli"), 0.98
                elif heading_match:
                    link_type, score = "symbol", 0.92
                else:
                    link_type, score = "symbol", 0.88
                links[(entity.id, section.id)] = CodeDocLink(
                    code_entity_id=entity.id,
                    documentation_section_id=section.id,
                    link_type=link_type,
                    similarity_score=score,
                    source="deterministic",
                    confidence=score,
                )
        return sorted(links.values(), key=lambda item: (item.code_entity_id, -item.confidence, item.documentation_section_id))

