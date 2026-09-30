from typing import Literal

from pydantic import Field

from .common import StrictModel


class Evidence(StrictModel):
    source: Literal["code", "documentation", "diff"]
    detail: str


class StalenessAnalysis(StrictModel):
    is_stale: bool
    confidence: float = Field(ge=0, le=1)
    severity: Literal["low", "medium", "high", "critical"]
    reason: str
    evidence: list[Evidence]
    affected_claims: list[str] = Field(default_factory=list)
    recommended_action: Literal["none", "repair", "human_review"]


class Decision(StrictModel):
    action: Literal["AUTO_FIX", "HUMAN_REVIEW", "REPORT_ONLY"]
    confidence: float = Field(ge=0, le=1)
    reason: str

