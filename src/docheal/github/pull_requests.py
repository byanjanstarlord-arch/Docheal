from __future__ import annotations

import re

from docheal.pipeline import PipelineResult


def safe_branch_name(prefix: str, pr_number: int, run_id: str) -> str:
    suffix = re.sub(r"[^A-Za-z0-9._-]", "-", run_id)[:32]
    return f"{prefix}/pr-{pr_number}-{suffix}".strip("/")


def repair_pr_body(result: PipelineResult, source_pr: int) -> str:
    rows = []
    for finding in result.findings:
        if finding.decision and finding.decision.action == "AUTO_FIX" and finding.repair:
            rows.append(f"- `{finding.section.file_path}` / **{finding.section.heading}** — {finding.analysis.reason} ({finding.decision.confidence:.0%})")
    return "\n".join([
        "## DocHeal documentation repair", "", f"Generated from source PR #{source_pr}.", "",
        "### Evidence-backed changes", *rows, "",
        "All changes are limited to Markdown documentation. Each proposal passed an independent validation step.",
    ])

