from docheal.decision import ConfidenceEngine
from docheal.models import (
    CodeDocLink,
    Evidence,
    RepairProposal,
    StalenessAnalysis,
    ValidationResult,
)


def fixtures():
    link = CodeDocLink(code_entity_id="a", documentation_section_id="b", link_type="symbol", similarity_score=1, source="deterministic", confidence=1)
    stale = StalenessAnalysis(is_stale=True, confidence=.96, severity="high", reason="missing", evidence=[Evidence(source="code", detail="parameter added")], affected_claims=["role"], recommended_action="repair")
    repair = RepairProposal(file_path="a.md", section_id="b", original_content="old", corrected_content="new", explanation="fixed", confidence=.97)
    valid = ValidationResult(valid=True, confidence=.96, correctness=.98, preservation_score=.97, style_consistency=.95, unsupported_claims=[], issues=[])
    return link, stale, repair, valid


def test_high_confidence_auto_fix():
    assert ConfidenceEngine().decide(*fixtures()).action == "AUTO_FIX"


def test_validation_failure_forces_review():
    link, stale, repair, valid = fixtures()
    valid.valid = False
    assert ConfidenceEngine().decide(link, stale, repair, valid).action == "HUMAN_REVIEW"


def test_disabled_auto_fix_forces_review():
    assert ConfidenceEngine().decide(*fixtures(), auto_fix_enabled=False).action == "HUMAN_REVIEW"

