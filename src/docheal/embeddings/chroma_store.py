from __future__ import annotations

from pathlib import Path
from typing import Any

from docheal.embeddings.provider import EmbeddingProvider
from docheal.errors import EmbeddingError


class ChromaStore:
    """Thin optional Chroma persistence adapter; import is delayed for deterministic local tests."""

    def __init__(self, path: Path, collection: str = "docheal") -> None:
        try:
            import chromadb
        except ImportError as exc:
            raise EmbeddingError("ChromaDB is not installed; install the project runtime dependencies") from exc
        self.client = chromadb.PersistentClient(path=str(path))
        self.collection = self.client.get_or_create_collection(collection, metadata={"hnsw:space": "cosine"})

    def upsert(self, ids: list[str], embeddings: list[list[float]], documents: list[str], metadatas: list[dict[str, str]]) -> None:
        self.collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)

    def query(self, embedding: list[float], count: int = 5) -> dict:
        return self.collection.query(query_embeddings=[embedding], n_results=count)

    def get_or_embed(
        self,
        ids: list[str],
        texts: list[str],
        content_hashes: list[str],
        metadatas: list[dict[str, Any]],
        provider: EmbeddingProvider,
    ) -> list[list[float]]:
        """Reuse unchanged vectors by content hash and embed only cache misses."""
        if not ids:
            return []
        cached = self.collection.get(ids=ids, include=["embeddings", "metadatas"])
        existing: dict[str, tuple[list[float], dict]] = {}
        for item_id, vector, metadata in zip(cached.get("ids", []), cached.get("embeddings", []), cached.get("metadatas", [])):
            existing[item_id] = (list(vector), metadata or {})
        result: list[list[float] | None] = [None] * len(ids)
        missing: list[int] = []
        for index, (item_id, digest) in enumerate(zip(ids, content_hashes)):
            row = existing.get(item_id)
            if row and row[1].get("content_hash") == digest:
                result[index] = row[0]
            else:
                missing.append(index)
        if missing:
            vectors = provider.embed([texts[index] for index in missing])
            if len(vectors) != len(missing):
                raise EmbeddingError("embedding provider returned an unexpected vector count")
            cache_metadata: list[dict[str, Any]] = []
            for index, vector in zip(missing, vectors):
                result[index] = vector
                cache_metadata.append({**metadatas[index], "content_hash": content_hashes[index]})
            self.collection.upsert(
                ids=[ids[index] for index in missing], embeddings=vectors,
                documents=[texts[index] for index in missing], metadatas=cache_metadata,
            )
        if any(vector is None for vector in result):
            raise EmbeddingError("embedding cache could not resolve every requested vector")
        return [vector for vector in result if vector is not None]
