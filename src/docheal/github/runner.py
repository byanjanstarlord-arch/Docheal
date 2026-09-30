from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path

from docheal.config import load_config
from docheal.embeddings import OpenAIEmbeddingProvider
from docheal.errors import DocHealError, EmbeddingError
from docheal.github.client import GitHubClient
from docheal.github.pull_requests import repair_pr_body, safe_branch_name
from docheal.llm import OpenAIProvider
from docheal.logging import configure_logging, log_event
from docheal.pipeline import AnalysisPipeline, build_index, changes_from_git
from docheal.reporting import github_comment, terminal_report


def _bool_input(name: str, default: bool) -> bool:
    value = os.getenv(f"INPUT_{name.upper()}")
    return default if value is None or value == "" else value.lower() in {"1", "true", "yes"}


def _set_output(name: str, value: object) -> None:
    output = os.getenv("GITHUB_OUTPUT")
    if output:
        with Path(output).open("a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")


def run_action(run_id: str | None = None) -> int:
    run_id = run_id or configure_logging()
    logger = logging.getLogger("docheal.action")
    event_path = Path(os.environ["GITHUB_EVENT_PATH"])
    event = json.loads(event_path.read_text(encoding="utf-8"))
    pull = event.get("pull_request")
    if not pull:
        raise DocHealError("DocHeal Action currently requires a pull_request event")
    repository = Path(os.getenv("GITHUB_WORKSPACE", ".")).resolve()
    log_event(
        logger, "action_started", run_id=run_id, repository=os.getenv("GITHUB_REPOSITORY"),
        pr_number=pull["number"],
    )
    requested_config = os.getenv("INPUT_CONFIG_PATH")
    if requested_config:
        config_path = (repository / requested_config).resolve()
        try:
            config_path.relative_to(repository)
        except ValueError as exc:
            raise DocHealError("configuration path escapes the repository") from exc
    else:
        candidates = [
            Path(value) for value in [
                os.getenv("DOCHEAL_DEFAULT_CONFIG"),
                str(Path(__file__).resolve().parents[3] / "config" / "default.yaml"),
            ] if value
        ]
        config_path = next((candidate for candidate in candidates if candidate.is_file()), None)
    config = load_config(config_path)
    if value := os.getenv("INPUT_SOURCE_DIRECTORIES"):
        config.source.include = [item.strip() for item in value.split(",") if item.strip()]
    if value := os.getenv("INPUT_DOCUMENTATION_PATHS"):
        config.documentation.include = [item.strip() for item in value.split(",") if item.strip()]
    if value := os.getenv("INPUT_LLM_MODEL"):
        config.llm.model = value
    if value := os.getenv("INPUT_EMBEDDING_MODEL"):
        config.embeddings.model = value
    if value := os.getenv("INPUT_CONFIDENCE_THRESHOLD"):
        config.decision.auto_fix_threshold = float(value)
    if value := os.getenv("INPUT_SEMANTIC_SIMILARITY_THRESHOLD"):
        config.embeddings.similarity_threshold = float(value)
    config.github.auto_fix_enabled = _bool_input("auto_fix_enabled", config.github.auto_fix_enabled)
    # A branch in a fork cannot safely be targeted by a branch created in the base repository.
    # Keep the analysis useful, but force human review for fork-originated pull requests.
    if pull.get("head", {}).get("repo", {}).get("full_name") != os.getenv("GITHUB_REPOSITORY"):
        config.github.auto_fix_enabled = False
    api_key = os.getenv("INPUT_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key

    embedding = OpenAIEmbeddingProvider(config.embeddings.model, api_key)
    try:
        index = build_index(repository, config, embedding)
    except EmbeddingError as exc:
        log_event(logger, "embedding_fallback", run_id=run_id, error=str(exc))
        index = build_index(repository, config)
    changes = changes_from_git(repository, pull["base"]["sha"], pull["head"]["sha"])
    log_event(
        logger, "changes_analyzed", run_id=run_id, changed_entities=len(changes),
        model=config.llm.model, embedding_model=config.embeddings.model,
        embedding_usage=embedding.usage,
    )
    provider = OpenAIProvider(config.llm.model, api_key, config.llm.timeout_seconds)
    result = AnalysisPipeline(config, provider).run(changes, index)
    log_event(
        logger, "analysis_completed", run_id=run_id, sections_checked=result.sections_checked,
        stale_sections=result.stale_count, repairs_generated=result.repairs_generated,
        repairs_validated=result.repairs_validated, model_usage=provider.usage,
        decisions=[item.decision.action for item in result.findings if item.decision],
        confidences=[item.decision.confidence for item in result.findings if item.decision],
    )

    token = os.getenv("INPUT_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN")
    repository_name = os.environ["GITHUB_REPOSITORY"]
    client = GitHubClient(token or "", repository_name)
    fix_url = None
    repairs = [
        (item.repair.file_path, item.repair.original_content, item.repair.corrected_content)
        for item in result.findings
        if item.decision and item.decision.action == "AUTO_FIX" and item.repair
    ]
    if repairs:
        github_run_id = os.getenv("GITHUB_RUN_ID", str(uuid.uuid4()))
        branch = safe_branch_name(config.github.branch_prefix, pull["number"], github_run_id)
        fix_url = client.create_documentation_pr(
            base_branch=pull["head"]["ref"], branch_name=branch,
            title=f"docs: synchronize documentation for #{pull['number']}",
            body=repair_pr_body(result, pull["number"]), replacements=repairs,
        )
    client.upsert_pr_comment(pull["number"], github_comment(result, fix_url))
    _set_output("sections_checked", result.sections_checked)
    _set_output("stale_sections", result.stale_count)
    _set_output("repairs_generated", result.repairs_generated)
    _set_output("repairs_validated", result.repairs_validated)
    _set_output("human_review_items", sum(bool(item.decision and item.decision.action == "HUMAN_REVIEW") for item in result.findings))
    _set_output("created_pr_url", fix_url or "")
    print(terminal_report(result))
    log_event(logger, "action_completed", run_id=run_id, created_pr=bool(fix_url))
    return 0
