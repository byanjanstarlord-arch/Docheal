from __future__ import annotations

from pydantic import ValidationError as PydanticValidationError

from docheal.errors import LLMError
from docheal.llm import LLMProvider
from docheal.models import CodeEntity, DocumentationSection, RepairProposal, StalenessAnalysis
from docheal.prompts import load_prompt


class RepairGenerator:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    def generate(self, entity: CodeEntity, section: DocumentationSection, analysis: StalenessAnalysis) -> RepairProposal:
        user = "\n".join([
            f"Target file: {section.file_path}", f"Target section ID: {section.id}",
            "<UNTRUSTED_CURRENT_SECTION>", section.content, "</UNTRUSTED_CURRENT_SECTION>",
            "<UNTRUSTED_NEW_CODE>", entity.source_code, "</UNTRUSTED_NEW_CODE>",
            "<TRUSTED_DIAGNOSIS_JSON>", analysis.model_dump_json(), "</TRUSTED_DIAGNOSIS_JSON>",
            "The original_content field must exactly equal the supplied current section.",
        ])
        try:
            raw = self.provider.complete_json(load_prompt("repair_v1"), user, "repair_proposal", RepairProposal.model_json_schema())
            proposal = RepairProposal.model_validate(raw)
        except PydanticValidationError as exc:
            raise LLMError(f"malformed repair response rejected: {exc}") from exc
        if proposal.file_path != section.file_path or proposal.section_id != section.id or proposal.original_content != section.content:
            raise LLMError("repair response changed immutable target metadata")
        return proposal

