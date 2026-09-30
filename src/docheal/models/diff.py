from typing import Literal

from pydantic import Field

from .common import StrictModel


class ChangedFile(StrictModel):
    old_path: str | None
    new_path: str | None
    change_type: Literal["added", "modified", "deleted", "renamed"]
    added_lines: list[int] = Field(default_factory=list)
    removed_lines: list[int] = Field(default_factory=list)
    patch: str = ""


class ChangedEntity(StrictModel):
    entity_id: str
    old_source: str | None = None
    new_source: str | None = None
    change_type: Literal["added", "removed", "modified", "signature_changed"]
    changed_lines: list[int] = Field(default_factory=list)
    significance: float = Field(ge=0, le=1)
    reason: str

