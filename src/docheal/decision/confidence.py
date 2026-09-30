from __future__ import annotations

from dataclasses import dataclass

from docheal.models import (
    CodeDocLink,
    Decision,
    RepairProposal,
    StalenessAnalysis,
    ValidationResult,
)


@dataclass(frozen=True)
class ConfidenceWeights:
    mapping: float = 0.15
    staleness: float = 0.30
    repair: float = 0.20
    validation: float = 0.35


class ConfidenceEngine:
    def __init__(self, auto_fix_threshold: float = 0.90, human_review_threshold: float = 0.70, weights: ConfidenceWeights | None = None) -> None:
        if not 0 <= human_review_threshold <= auto_fix_threshold <= 1:
            raise ValueError("decision thresholds must satisfy 0 <= review <= auto-fix <= 1")
        self.auto_fix_threshold = auto_fix_threshold
        self.human_review_threshold = human_review_threshold
        self.weights = weights or ConfidenceWeights()

    def decide(
        self,
        link: CodeDocLink,
        analysis: StalenessAnalysis,
        proposal: RepairProposal | None = None,
        validation: ValidationResult | None = None,
        auto_fix_enabled: bool = True,
    ) -> Decision:
        if not analysis.is_stale:
            return Decision(action="REPORT_ONLY", confidence=analysis.confidence, reason="documentation verified accurate")
        if proposal is None or validation is None or not validation.valid or validation.unsupported_claims:
            confidence = min(analysis.confidence, validation.confidence if validation else analysis.confidence)
            return Decision(action="HUMAN_REVIEW", confidence=confidence, reason="repair is absent or did not pass the independent validation gate")
        w = self.weights
        confidence = (
            link.confidence * w.mapping + analysis.confidence * w.staleness + proposal.confidence * w.repair + validation.confidence * w.validation
        ) / (w.mapping + w.staleness + w.repair + w.validation)
        confidence = round(confidence, 4)
        if confidence >= self.auto_fix_threshold and auto_fix_enabled:
            return Decision(action="AUTO_FIX", confidence=confidence, reason="all evidence and repair quality gates passed")
        if confidence >= self.human_review_threshold:
            reason = "auto-fix is disabled" if not auto_fix_enabled and confidence >= self.auto_fix_threshold else "confidence is below the auto-fix threshold"
            return Decision(action="HUMAN_REVIEW", confidence=confidence, reason=reason)
        return Decision(action="REPORT_ONLY", confidence=confidence, reason="evidence confidence is below the human-review threshold")
