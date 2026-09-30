from __future__ import annotations

from docheal.pipeline import PipelineResult

MARKER = "<!-- docheal-report:v1 -->"


def github_comment(result: PipelineResult, fix_pr_url: str | None = None) -> str:
    lines = [MARKER, "## 🤖 DocHeal Documentation Check", "", f"**{result.sections_checked}** documentation sections checked"]
    accurate = sum(bool(item.analysis and not item.analysis.is_stale) for item in result.findings)
    lines.extend([f"- ✅ {accurate} verified accurate", f"- ⚠️ {result.stale_count} require attention"])
    for item in result.findings:
        if not item.analysis or not item.analysis.is_stale:
            continue
        lines.extend([
            "", f"### `{item.section.file_path}` — {item.section.heading}", "",
            item.analysis.reason, "",
            f"**Staleness confidence:** {item.analysis.confidence:.0%}",
            f"**Decision:** {item.decision.action.replace('_', ' ').title() if item.decision else 'Human Review'}",
        ])
        if item.error:
            lines.append(f"**Safe failure:** {item.error}")
    if fix_pr_url:
        lines.extend(["", f"Documentation fix PR: {fix_pr_url}"])
    return "\n".join(lines).strip() + "\n"


def terminal_report(result: PipelineResult) -> str:
    lines = [
        "=" * 50, "DocHeal", "=" * 50,
        f"Changed code entities: {result.entities_changed}",
        f"Documentation sections checked: {result.sections_checked}",
        f"Stale sections found: {result.stale_count}",
    ]
    for item in result.findings:
        lines.extend(["", f"Affected: {item.section.file_path}", f"Section: {item.section.heading}"])
        if item.analysis:
            lines.extend([
                f"Staleness: {'CONFIRMED' if item.analysis.is_stale else 'NOT STALE'}",
                f"Confidence: {item.analysis.confidence:.2f}", f"Reason: {item.analysis.reason}",
            ])
        if item.repair:
            lines.append("Repair: Generated")
        if item.validation:
            lines.append(f"Validation: {'PASSED' if item.validation.valid else 'FAILED'}")
        if item.decision:
            lines.append(f"Decision: {item.decision.action}")
        if item.error:
            lines.append(f"Error: {item.error}")
    lines.append("=" * 50)
    return "\n".join(lines)

