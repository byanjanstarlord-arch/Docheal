from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
import tempfile
from pathlib import Path

from docheal.config import AppConfig, load_config
from docheal.demo_provider import DemoLLMProvider
from docheal.diff import DiffAnalyzer
from docheal.embeddings import OpenAIEmbeddingProvider
from docheal.errors import DocHealError, EmbeddingError
from docheal.llm import OpenAIProvider
from docheal.logging import configure_logging, log_event
from docheal.mapping.graph import RepositoryIndex
from docheal.parser import PythonParser
from docheal.pipeline import AnalysisPipeline, build_index, changes_from_git
from docheal.repair import DocumentationPatcher
from docheal.reporting import terminal_report
from docheal.scanner import RepositoryScanner


def _repository(value: str) -> Path:
    path = Path(value).resolve()
    if not path.is_dir():
        raise argparse.ArgumentTypeError(f"repository does not exist: {value}")
    return path


def _config(args: argparse.Namespace) -> AppConfig:
    path = Path(args.config).resolve() if args.config else None
    return load_config(path)


def command_scan(args: argparse.Namespace) -> int:
    entities, sections = RepositoryScanner(_config(args)).scan(args.repository)
    print(json.dumps({"repository": str(args.repository), "code_entities": len(entities), "documentation_sections": len(sections)}, indent=2))
    return 0


def command_index(args: argparse.Namespace) -> int:
    config = _config(args)
    provider = OpenAIEmbeddingProvider(config.embeddings.model) if args.semantic else None
    try:
        index = build_index(args.repository, config, provider)
    except EmbeddingError as exc:
        print(f"Semantic indexing unavailable; deterministic links were retained: {exc}", file=sys.stderr)
        index = build_index(args.repository, config)
    print(json.dumps({"index": str(args.repository / config.index.path), "entities": len(index.code_entities), "sections": len(index.documentation_sections), "links": len(index.links)}, indent=2))
    return 0


def _index_and_changes(args: argparse.Namespace) -> tuple[AppConfig, RepositoryIndex, list]:
    config = _config(args)
    index_path = args.repository / config.index.path
    index = RepositoryIndex.load(index_path) if index_path.is_file() and not args.refresh_index else build_index(args.repository, config)
    return config, index, changes_from_git(args.repository, args.base, args.head)


def command_analyze(args: argparse.Namespace) -> int:
    _config_value, index, changes = _index_and_changes(args)
    links = {change.entity_id: len(index.sections_for(change.entity_id)) for change in changes}
    print(json.dumps({"changed_entities": [item.model_dump(mode="json") for item in changes], "candidate_sections": links}, indent=2))
    return 0


def _verify(args: argparse.Namespace, apply: bool = False) -> int:
    config, index, changes = _index_and_changes(args)
    provider = OpenAIProvider(config.llm.model, timeout=config.llm.timeout_seconds)
    result = AnalysisPipeline(config, provider).run(changes, index)
    if apply:
        patcher = DocumentationPatcher()
        for finding in result.findings:
            if finding.decision and finding.decision.action == "AUTO_FIX" and finding.repair:
                patcher.apply(args.repository, finding.repair)
    print(terminal_report(result))
    return 2 if any(item.error for item in result.findings) else 0


def command_verify(args: argparse.Namespace) -> int:
    return _verify(args, apply=False)


def command_repair(args: argparse.Namespace) -> int:
    return _verify(args, apply=args.apply)


def command_demo(args: argparse.Namespace) -> int:
    demo_root = Path.cwd() / "demo"
    if (demo_root / "repository").is_dir():
        return _run_demo(demo_root, apply=args.apply)
    if args.apply:
        raise DocHealError("--apply requires running the demo from a DocHeal source checkout")
    packaged_demo = Path(__file__).resolve().parents[1] / "demo_data"
    with tempfile.TemporaryDirectory(prefix="docheal-demo-") as temporary:
        demo_root = Path(temporary) / "demo"
        shutil.copytree(packaged_demo, demo_root)
        return _run_demo(demo_root, apply=False)


def _run_demo(demo_root: Path, *, apply: bool) -> int:
    repository = demo_root / "repository"
    config = AppConfig()
    config.github.auto_fix_enabled = True
    index = build_index(repository, config, persist=False)
    parser = PythonParser()
    before_source = (demo_root / "before" / "users.py").read_text(encoding="utf-8")
    before = parser.parse_text(before_source, "src/users.py")
    after = parser.parse_file(repository / "src" / "users.py", repository)
    changes = DiffAnalyzer().compare_entities(before, after)
    result = AnalysisPipeline(config, DemoLLMProvider()).run(changes, index)
    print(terminal_report(result))
    if apply:
        for finding in result.findings:
            if finding.decision and finding.decision.action == "AUTO_FIX" and finding.repair:
                DocumentationPatcher().apply(repository, finding.repair)
    return 0 if result.stale_count and result.repairs_validated else 1


def command_github_action(args: argparse.Namespace) -> int:
    from docheal.github.runner import run_action

    return run_action(args.run_id)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="docheal", description="Keep documentation synchronized with Python code.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def common(name: str, handler, *, diff: bool = False) -> argparse.ArgumentParser:
        command = subparsers.add_parser(name)
        command.add_argument("--repository", "--repo", type=_repository, default=Path.cwd())
        command.add_argument("--config")
        if diff:
            command.add_argument("--base", default="HEAD~1")
            command.add_argument("--head", default="HEAD")
            command.add_argument("--refresh-index", action="store_true")
        command.set_defaults(handler=handler)
        return command

    common("scan", command_scan)
    index = common("index", command_index)
    index.add_argument("--semantic", action="store_true", help="add embedding-based links")
    common("analyze", command_analyze, diff=True)
    common("verify", command_verify, diff=True)
    repair = common("repair", command_repair, diff=True)
    repair.add_argument("--apply", action="store_true", help="apply only validated AUTO_FIX documentation patches")
    demo = subparsers.add_parser("demo")
    demo.add_argument("--apply", action="store_true")
    demo.set_defaults(handler=command_demo)
    action = subparsers.add_parser("github-action", help=argparse.SUPPRESS)
    action.set_defaults(handler=command_github_action)
    return parser


def main(argv: list[str] | None = None) -> int:
    run_id = configure_logging()
    logger = logging.getLogger("docheal.cli")
    try:
        args = build_parser().parse_args(argv)
        args.run_id = run_id
        log_event(logger, "run_started", run_id=run_id, command=args.command)
        status = args.handler(args)
        log_event(logger, "run_completed", run_id=run_id, command=args.command, status=status)
        return status
    except (DocHealError, OSError, ValueError) as exc:
        log_event(logger, "run_failed", run_id=run_id, error_type=type(exc).__name__, error=str(exc))
        print(f"DocHeal error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
