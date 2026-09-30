from __future__ import annotations

from pydantic import ValidationError as PydanticValidationError

from docheal.errors import LLMError
from docheal.llm import LLMProvider
from docheal.models import ChangedEntity, DocumentationSection, StalenessAnalysis
from docheal.prompts import load_prompt


class StaleDocumentationDetector:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    def analyze(self, change: ChangedEntity, section: DocumentationSection) -> StalenessAnalysis:
        user = "\n".join([
            "Analyze this code/documentation relationship.",
            f"Change type: {change.change_type}", f"Change significance: {change.significance}",
            "<UNTRUSTED_OLD_CODE>", change.old_source or "(entity did not exist)", "</UNTRUSTED_OLD_CODE>",
            "<UNTRUSTED_NEW_CODE>", change.new_source or "(entity was removed)", "</UNTRUSTED_NEW_CODE>",
            "<UNTRUSTED_DOCUMENTATION>", section.content, "</UNTRUSTED_DOCUMENTATION>",
        ])
        try:
            raw = self.provider.complete_json(
                load_prompt("staleness_v1"), user, "staleness_analysis",
                StalenessAnalysis.model_json_schema(),
            )
            return StalenessAnalysis.model_validate(raw)
        except PydanticValidationError as exc:
            raise LLMError(f"malformed staleness response rejected: {exc}") from exc

