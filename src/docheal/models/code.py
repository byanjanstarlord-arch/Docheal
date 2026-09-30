from typing import Any, Literal

from pydantic import Field

from .common import StrictModel


class CodeEntity(StrictModel):
    id: str
    file_path: str
    symbol_name: str
    entity_type: Literal["module", "function", "class", "method", "constant", "endpoint", "cli"]
    qualified_name: str
    source_code: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    signature: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

