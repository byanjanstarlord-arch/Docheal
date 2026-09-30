from typing import Any, Literal

from pydantic import Field

from .common import StrictModel


class DocumentationSection(StrictModel):
    id: str
    file_path: str
    heading: str
    heading_path: list[str]
    content: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    referenced_symbols: list[str] = Field(default_factory=list)
    parent_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CodeDocLink(StrictModel):
    code_entity_id: str
    documentation_section_id: str
    link_type: Literal["symbol", "qualified_name", "signature", "route", "cli", "semantic"]
    similarity_score: float = Field(ge=0, le=1)
    source: Literal["deterministic", "embedding"]
    confidence: float = Field(ge=0, le=1)

