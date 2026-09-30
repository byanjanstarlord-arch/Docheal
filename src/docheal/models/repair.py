from pydantic import Field, model_validator

from .common import StrictModel


class RepairProposal(StrictModel):
    file_path: str
    section_id: str
    original_content: str
    corrected_content: str
    explanation: str
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def changed_content(self) -> "RepairProposal":
        if self.original_content == self.corrected_content:
            raise ValueError("repair must change section content")
        return self


class ValidationResult(StrictModel):
    valid: bool
    confidence: float = Field(ge=0, le=1)
    correctness: float = Field(ge=0, le=1)
    preservation_score: float = Field(ge=0, le=1)
    style_consistency: float = Field(ge=0, le=1)
    unsupported_claims: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)

