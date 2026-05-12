"""Cross-encoder reranking of retrieved chunks.

The retriever (bi-encoder) optimises for recall — fast nearest-neighbour search.
A cross-encoder re-scores each (query, chunk) pair with a deeper model that
attends to both jointly, dramatically improving precision. This is a standard
two-stage RAG pattern; the marginal latency (~50-200ms for top-20) buys
noticeably better top-k.

Public surface:
    - RerankedChunk: rerank result with both retrieval and rerank scores.
    - get_reranker(): singleton accessor.
    - Reranker.rerank(): rerank a list of RetrievedChunk down to top-k.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

from sentence_transformers import CrossEncoder

from config import get_settings
from pipeline.retriever import RetrievedChunk

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RerankedChunk:
    chunk_id: str
    text: str
    metadata: dict[str, str | int]
    retrieval_similarity: float
    rerank_score: float

    def to_payload(self) -> dict:
        """Frontend-friendly serialisation for the pipeline visualizer."""
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "metadata": self.metadata,
            "retrieval_similarity": self.retrieval_similarity,
            "rerank_score": round(self.rerank_score, 4),
        }


class Reranker:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._model: CrossEncoder | None = None
        self._lock = threading.Lock()

    def _get_model(self) -> CrossEncoder:
        if self._model is None:
            with self._lock:
                if self._model is None:
                    logger.info("Loading cross-encoder: %s", self._settings.reranker_model)
                    self._model = CrossEncoder(self._settings.reranker_model)
        return self._model

    def rerank(
        self,
        query: str,
        candidates: list[RetrievedChunk],
        top_k: int | None = None,
    ) -> list[RerankedChunk]:
        if not candidates:
            return []
        if not query.strip():
            return []

        k = top_k or self._settings.rerank_top_k
        model = self._get_model()

        pairs = [(query, c.text) for c in candidates]
        # `.predict` returns numpy array of float scores (logits-like).
        raw_scores = model.predict(pairs, show_progress_bar=False)
        scored = sorted(
            zip(candidates, (float(s) for s in raw_scores)),
            key=lambda x: x[1],
            reverse=True,
        )[:k]

        return [
            RerankedChunk(
                chunk_id=c.chunk_id,
                text=c.text,
                metadata=c.metadata,
                retrieval_similarity=c.similarity,
                rerank_score=score,
            )
            for c, score in scored
        ]


_reranker_singleton: Reranker | None = None
_reranker_lock = threading.Lock()


def get_reranker() -> Reranker:
    global _reranker_singleton
    if _reranker_singleton is None:
        with _reranker_lock:
            if _reranker_singleton is None:
                _reranker_singleton = Reranker()
    return _reranker_singleton
