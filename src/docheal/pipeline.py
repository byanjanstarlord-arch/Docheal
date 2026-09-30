from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from docheal.config import AppConfig
from docheal.decision import ConfidenceEngine
from docheal.detection import AffectedDocumentationResolver, StaleDocumentationDetector
from docheal.diff import DiffAnalyzer
from docheal.errors import EmbeddingError, LLMError
from docheal.llm import LLMProvider
from docheal.mapping import HeuristicMapper, SemanticMapper
from docheal.mapping.graph import RepositoryIndex
from docheal.models import (
    ChangedEntity,
    CodeDocLink,
    Decision,
    DocumentationSection,
    RepairProposal,
    StalenessAnalysis,
    ValidationResult,
)
from docheal.repair import RepairGenerator
from docheal.repository import GitRepository
from docheal.scanner import RepositoryScanner
from docheal.validation import RepairValidator


@dataclass
class Finding:
    change: ChangedEntity
    section: DocumentationSection
    link: CodeDocLink
    analysis: StalenessAnalysis | None = None
    repair: RepairProposal | None = None
    validation: ValidationResult | None = None
    decision: Decision | None = None
    error: str | None = None


@dataclass
class PipelineResult:
    entities_changed: int
    sections_checked: int = 0
    findings: list[Finding] = field(default_factory=list)

    @property
    def stale_count(self) -> int:
        return sum(bool(item.analysis and item.analysis.is_stale) for item in self.findings)

    @property
    def repairs_generated(self) -> int:
        return sum(item.repair is not None for item in self.findings)

    @property
    def repairs_validated(self) -> int:
        return sum(bool(item.validation and item.validation.valid) for item in self.findings)


def build_index(
    repository: Path, config: AppConfig, embedding_provider=None, *, persist: bool = True
) -> RepositoryIndex:
    entities, sections = RepositoryScanner(config).scan(repository)
    links = HeuristicMapper().map(entities, sections)
    if embedding_provider is not None:
        mapper = SemanticMapper(embedding_provider, config.embeddings.similarity_threshold)
        try:
            from docheal.embeddings.chroma_store import ChromaStore

            store = ChromaStore(repository / config.index.chroma_path, config.embeddings.collection)
            code_texts, doc_texts = mapper.inputs(entities, sections)
            code_vectors = store.get_or_embed(
                [f"code:{item.id}" for item in entities], code_texts,
                [str(item.metadata.get("content_hash", "")) for item in entities],
                [{"kind": "code", "path": item.file_path} for item in entities], embedding_provider,
            )
            doc_vectors = store.get_or_embed(
                [f"doc:{item.id}" for item in sections], doc_texts,
                [str(item.metadata.get("content_hash", "")) for item in sections],
                [{"kind": "documentation", "path": item.file_path} for item in sections], embedding_provider,
            )
            semantic = mapper.map_vectors(entities, sections, code_vectors, doc_vectors)
        except EmbeddingError:
            semantic = mapper.map(entities, sections)
        existing = {(link.code_entity_id, link.documentation_section_id) for link in links}
        links.extend(link for link in semantic if (link.code_entity_id, link.documentation_section_id) not in existing)
    index = RepositoryIndex(code_entities=entities, documentation_sections=sections, links=links)
    if persist:
        index.save(repository / config.index.path)
    return index


def changes_from_git(repository: Path, base: str, head: str = "HEAD") -> list[ChangedEntity]:
    git = GitRepository(repository)
    analyzer = DiffAnalyzer()
    changes: list[ChangedEntity] = []
    for changed_file in analyzer.parse_unified_diff(git.diff(base, head)):
        old_path = changed_file.old_path or changed_file.new_path
        new_path = changed_file.new_path or changed_file.old_path
        if not (old_path and new_path and new_path.endswith(".py")):
            continue
        from docheal.parser import PythonParser

        parser = PythonParser()
        old_source = git.show(base, old_path)
        new_source = git.show(head, new_path) if head != "WORKTREE" else git.current_text(new_path)
        old_entities = parser.parse_text(old_source, old_path) if old_source is not None else []
        new_entities = parser.parse_text(new_source, new_path) if new_source is not None else []
        changes.extend(analyzer.compare_entities(old_entities, new_entities))
    return changes


class AnalysisPipeline:
    def __init__(self, config: AppConfig, provider: LLMProvider) -> None:
        self.config = config
        self.detector = StaleDocumentationDetector(provider)
        self.generator = RepairGenerator(provider)
        self.validator = RepairValidator(provider)
        self.confidence = ConfidenceEngine(
            config.decision.auto_fix_threshold, config.decision.human_review_threshold
        )

    def run(self, changes: list[ChangedEntity], index: RepositoryIndex) -> PipelineResult:
        result = PipelineResult(entities_changed=len(changes))
        entities = {item.id: item for item in index.code_entities}
        affected = AffectedDocumentationResolver().resolve(changes, index)
        by_change = {item.entity_id: item for item in changes}
        for entity_id, matches in affected.items():
            change = by_change[entity_id]
            entity = entities.get(entity_id)
            for section, link in matches:
                finding = Finding(change=change, section=section, link=link)
                result.sections_checked += 1
                try:
                    finding.analysis = self.detector.analyze(change, section)
                    if finding.analysis.is_stale and entity is not None and change.new_source is not None:
                        finding.repair = self.generator.generate(entity, section, finding.analysis)
                        finding.validation = self.validator.validate(entity, finding.analysis, finding.repair)
                    finding.decision = self.confidence.decide(
                        link, finding.analysis, finding.repair, finding.validation,
                        auto_fix_enabled=self.config.github.auto_fix_enabled,
                    )
                except LLMError as exc:
                    finding.error = str(exc)
                    finding.decision = Decision(action="HUMAN_REVIEW", confidence=0, reason="LLM stage failed closed")
                result.findings.append(finding)
        return result
