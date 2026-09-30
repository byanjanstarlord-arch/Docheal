from __future__ import annotations

from pydantic import ValidationError as PydanticValidationError

from docheal.errors import LLMError
from docheal.llm import LLMProvider
from docheal.models import CodeEntity, RepairProposal, StalenessAnalysis, ValidationResult
from docheal.prompts import load_prompt


class RepairValidator:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    def validate(self, entity: CodeEntity, analysis: StalenessAnalysis, proposal: RepairProposal) -> ValidationResult:
        user = (
            f"<UNTRUSTED_NEW_CODE>\n{entity.source_code}\n</UNTRUSTED_NEW_CODE>\n"
            f"<TRUSTED_DIAGNOSIS_JSON>\n{analysis.model_dump_json()}\n</TRUSTED_DIAGNOSIS_JSON>\n"
            f"<UNTRUSTED_ORIGINAL_DOCUMENTATION>\n{proposal.original_content}\n"
            f"</UNTRUSTED_ORIGINAL_DOCUMENTATION>\n<UNTRUSTED_PROPOSED_DOCUMENTATION>\n"
            f"{proposal.corrected_content}\n</UNTRUSTED_PROPOSED_DOCUMENTATION>"
        )
        try:
            raw = self.provider.complete_json(load_prompt("validation_v1"), user, "validation_result", ValidationResult.model_json_schema())
            return ValidationResult.model_validate(raw)
        except PydanticValidationError as exc:
            raise LLMError(f"malformed validation response rejected: {exc}") from exc
