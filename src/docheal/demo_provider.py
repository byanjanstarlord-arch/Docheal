from __future__ import annotations

import re
from typing import Any


class DemoLLMProvider:
    """Deterministic provider used only by the built-in demo and tests, never by Action runs."""

    def complete_json(self, system: str, user: str, schema_name: str, schema: dict[str, Any]) -> dict[str, Any]:
        del system, schema
        if schema_name == "staleness_analysis":
            new_code = self._block(user, "UNTRUSTED_NEW_CODE")
            docs = self._block(user, "UNTRUSTED_DOCUMENTATION")
            parameters = self._parameters(new_code)
            documented_signature = re.search(r"`\w+\(([^`]*)\)`", docs)
            documented_parameters = self._parameter_list(documented_signature.group(1)) if documented_signature else []
            missing = [item for item in parameters if item not in documented_parameters]
            stale = bool(missing)
            return {
                "is_stale": stale, "confidence": 0.96 if stale else 0.91,
                "severity": "high" if stale else "low",
                "reason": f"Documentation does not mention parameter(s): {', '.join(missing)}." if stale else "Documentation remains consistent with the callable interface.",
                "evidence": ([{"source": "code", "detail": f"New signature includes {', '.join(missing)}"}, {"source": "documentation", "detail": "The section omits those parameters"}] if stale else [{"source": "documentation", "detail": "Documented parameters match the signature"}]),
                "affected_claims": missing, "recommended_action": "repair" if stale else "none",
            }
        if schema_name == "repair_proposal":
            original = self._block(user, "UNTRUSTED_CURRENT_SECTION")
            code = self._block(user, "UNTRUSTED_NEW_CODE")
            file_path = re.search(r"Target file: (.+)", user).group(1).strip()
            section_id = re.search(r"Target section ID: (.+)", user).group(1).strip()
            signature = re.search(r"(?:async )?def\s+\w+\([^)]*\)(?:\s*->\s*[^:\n]+)?", code)
            replacement = original
            current_signature = re.search(r"`[^`]+\([^`]*\)`", original)
            if signature and current_signature:
                replacement = original[:current_signature.start()] + f"`{signature.group(0).removeprefix('def ').removeprefix('async def ')}`" + original[current_signature.end():]
            return {"file_path": file_path, "section_id": section_id, "original_content": original, "corrected_content": replacement, "explanation": "Updated the documented signature to match the code.", "confidence": 0.97}
        if schema_name == "validation_result":
            original = self._block(user, "UNTRUSTED_ORIGINAL_DOCUMENTATION")
            proposed = self._block(user, "UNTRUSTED_PROPOSED_DOCUMENTATION")
            valid = original != proposed
            return {"valid": valid, "confidence": 0.96 if valid else 0.2, "correctness": 0.98 if valid else 0.2, "preservation_score": 0.98, "style_consistency": 0.98, "unsupported_claims": [], "issues": [] if valid else ["proposal made no change"]}
        raise ValueError(f"unsupported demo schema: {schema_name}")

    @staticmethod
    def _block(text: str, name: str) -> str:
        match = re.search(rf"<{name}>\n(.*?)\n</{name}>", text, re.DOTALL)
        return match.group(1) if match else ""

    @staticmethod
    def _parameters(code: str) -> list[str]:
        match = re.search(r"(?:async )?def\s+\w+\(([^)]*)\)", code)
        if not match:
            return []
        return DemoLLMProvider._parameter_list(match.group(1))

    @staticmethod
    def _parameter_list(parameters: str) -> list[str]:
        result = []
        for raw in parameters.split(","):
            name = raw.strip().lstrip("*").split(":", 1)[0].split("=", 1)[0].strip()
            if name and name not in {"self", "cls"}:
                result.append(name)
        return result
