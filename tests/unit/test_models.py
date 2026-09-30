import pytest
from pydantic import ValidationError

from docheal.models import CodeEntity, RepairProposal


def test_models_reject_unknown_fields():
    with pytest.raises(ValidationError):
        CodeEntity(id="a", file_path="a.py", symbol_name="a", entity_type="function", qualified_name="a", source_code="", start_line=1, end_line=1, surprise=True)


def test_repair_must_change_content():
    with pytest.raises(ValidationError):
        RepairProposal(file_path="a.md", section_id="x", original_content="same", corrected_content="same", explanation="none", confidence=.9)

