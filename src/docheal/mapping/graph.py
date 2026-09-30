from __future__ import annotations

import json
from pathlib import Path

from pydantic import Field

from docheal.models import CodeDocLink, CodeEntity, DocumentationSection
from docheal.models.common import StrictModel


class RepositoryIndex(StrictModel):
    schema_version: int = 1
    code_entities: list[CodeEntity] = Field(default_factory=list)
    documentation_sections: list[DocumentationSection] = Field(default_factory=list)
    links: list[CodeDocLink] = Field(default_factory=list)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        temporary.replace(path)

    @classmethod
    def load(cls, path: Path) -> RepositoryIndex:
        return cls.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def sections_for(self, entity_id: str) -> list[tuple[DocumentationSection, CodeDocLink]]:
        sections = {item.id: item for item in self.documentation_sections}
        matches = [(sections[link.documentation_section_id], link) for link in self.links if link.code_entity_id == entity_id and link.documentation_section_id in sections]
        return sorted(matches, key=lambda item: -item[1].confidence)
