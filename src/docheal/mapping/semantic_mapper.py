from __future__ import annotations

import math

from docheal.embeddings import EmbeddingProvider
from docheal.models import CodeDocLink, CodeEntity, DocumentationSection


def cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    denominator = math.sqrt(sum(value * value for value in left)) * math.sqrt(sum(value * value for value in right))
    return max(0.0, min(1.0, sum(a * b for a, b in zip(left, right)) / denominator)) if denominator else 0.0


class SemanticMapper:
    def __init__(self, provider: EmbeddingProvider, threshold: float = 0.80) -> None:
        self.provider = provider
        self.threshold = threshold

    def map(self, entities: list[CodeEntity], sections: list[DocumentationSection]) -> list[CodeDocLink]:
        if not entities or not sections:
            return []
        code_texts, doc_texts = self.inputs(entities, sections)
        vectors = self.provider.embed([*code_texts, *doc_texts])
        if len(vectors) != len(code_texts) + len(doc_texts):
            raise ValueError("embedding provider returned an unexpected vector count")
        return self.map_vectors(entities, sections, vectors[:len(entities)], vectors[len(entities):])

    @staticmethod
    def inputs(entities: list[CodeEntity], sections: list[DocumentationSection]) -> tuple[list[str], list[str]]:
        return (
            [f"{e.entity_type} {e.qualified_name}\n{e.signature or ''}\n{e.source_code}" for e in entities],
            [f"{' > '.join(s.heading_path)}\n{s.content}" for s in sections],
        )

    def map_vectors(
        self,
        entities: list[CodeEntity],
        sections: list[DocumentationSection],
        code_vectors: list[list[float]],
        doc_vectors: list[list[float]],
    ) -> list[CodeDocLink]:
        links: list[CodeDocLink] = []
        for code_index, entity in enumerate(entities):
            for doc_index, section in enumerate(sections):
                score = cosine(code_vectors[code_index], doc_vectors[doc_index])
                if score >= self.threshold:
                    links.append(CodeDocLink(
                        code_entity_id=entity.id,
                        documentation_section_id=section.id,
                        link_type="semantic",
                        similarity_score=score,
                        source="embedding",
                        confidence=score,
                    ))
        return sorted(links, key=lambda item: (item.code_entity_id, -item.similarity_score))
