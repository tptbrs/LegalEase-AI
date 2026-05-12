"""Vector retrieval over the ingested Indian Acts corpus.

A small, dependency-free vector store backed by NumPy:

  * Embeddings are stored as a single `embeddings.npy` (float32, L2-normalised).
  * Per-row records (chunk_id, text, metadata) live in a sibling `records.json`.
  * Cosine similarity is a single matrix-vector multiply because every vector
    is unit-normalised at insertion time.

For corpus sizes up to ~100k chunks this is fast (sub-10 ms queries on CPU)
and removes the need for a compiled ANN library — which is exactly the
portability win we want for a Windows / B.Tech-demo deployment.

Public surface (preserved from the prior ChromaDB version, so callers don't change):
    - RetrievedChunk
    - get_retriever()
    - Retriever.embed()
    - Retriever.add()
    - Retriever.delete_by_source()
    - Retriever.count()
    - Retriever.query()
    - Retriever.clear()
    - Retriever.all_records()
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from sentence_transformers import SentenceTransformer

from config import get_settings
from pipeline.ingestion import Chunk

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RetrievedChunk:
    """One row returned by `Retriever.query`."""

    chunk_id: str
    text: str
    metadata: dict[str, str | int]
    distance: float  # cosine distance in [0, 2]; lower = closer

    @property
    def similarity(self) -> float:
        """Convert distance to a [0, 1]-ish similarity score for display."""
        return round(max(0.0, 1.0 - self.distance), 4)


class Retriever:
    """NumPy-backed vector store + embedding model wrapper."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._settings.ensure_dirs()
        self._model: SentenceTransformer | None = None
        self._embeddings: np.ndarray = np.zeros((0, 0), dtype=np.float32)
        self._records: list[dict] = []
        self._id_to_idx: dict[str, int] = {}
        self._loaded = False
        self._lock = threading.Lock()

    # ----- Persistence paths -------------------------------------------------

    @property
    def _embeddings_path(self) -> Path:
        return self._settings.chroma_dir / "embeddings.npy"

    @property
    def _records_path(self) -> Path:
        return self._settings.chroma_dir / "records.json"

    # ----- Lazy components ---------------------------------------------------

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            with self._lock:
                if self._model is None:
                    logger.info("Loading embedding model: %s", self._settings.embedding_model)
                    self._model = SentenceTransformer(self._settings.embedding_model)
        return self._model

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            if self._embeddings_path.exists() and self._records_path.exists():
                self._embeddings = np.load(self._embeddings_path).astype(np.float32)
                self._records = json.loads(self._records_path.read_text(encoding="utf-8"))
                self._id_to_idx = {r["chunk_id"]: i for i, r in enumerate(self._records)}
                logger.info(
                    "Vector store loaded: %d records, dim=%d",
                    len(self._records),
                    self._embeddings.shape[1] if self._embeddings.ndim == 2 else 0,
                )
            else:
                self._embeddings = np.zeros((0, 0), dtype=np.float32)
                self._records = []
                self._id_to_idx = {}
            self._loaded = True

    def _persist(self) -> None:
        np.save(self._embeddings_path, self._embeddings)
        self._records_path.write_text(
            json.dumps(self._records, ensure_ascii=False),
            encoding="utf-8",
        )

    # ----- Embedding ---------------------------------------------------------

    def embed(self, texts: list[str]) -> np.ndarray:
        """Encode a batch of strings into normalised float32 embeddings."""
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)
        model = self._get_model()
        return model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype(np.float32)

    # ----- Write path --------------------------------------------------------

    def add(self, chunks: Iterable[Chunk], batch_size: int = 64) -> int:
        """Embed and upsert chunks. Returns the number of chunks added/updated.

        New rows are accumulated per batch and inserted with a single `np.vstack`
        per batch instead of one per row — O(batches) array copies instead of
        O(chunks), which makes ingest.py noticeably faster on large corpora.
        """
        self._ensure_loaded()
        added = 0
        buf: list[Chunk] = []

        def flush(batch: list[Chunk]) -> None:
            nonlocal added
            if not batch:
                return
            new_emb = self.embed([c.text for c in batch])

            fresh_emb: list[np.ndarray] = []
            fresh_records: list[dict] = []

            for c, emb in zip(batch, new_emb):
                record = {"chunk_id": c.chunk_id, "text": c.text, "metadata": c.metadata}
                if c.chunk_id in self._id_to_idx:
                    # In-place update is already O(1); no vstack needed.
                    idx = self._id_to_idx[c.chunk_id]
                    self._embeddings[idx] = emb
                    self._records[idx] = record
                else:
                    fresh_emb.append(emb)
                    fresh_records.append(record)
                added += 1

            if fresh_emb:
                new_block = np.vstack(fresh_emb).astype(np.float32)
                if self._embeddings.size == 0:
                    self._embeddings = new_block
                else:
                    self._embeddings = np.vstack(
                        [self._embeddings, new_block]
                    ).astype(np.float32)
                start_idx = len(self._records)
                for i, r in enumerate(fresh_records):
                    self._id_to_idx[r["chunk_id"]] = start_idx + i
                self._records.extend(fresh_records)

        for c in chunks:
            buf.append(c)
            if len(buf) >= batch_size:
                flush(buf)
                buf = []
        flush(buf)

        self._persist()
        return added

    def delete_by_source(self, source_pdf: str) -> int:
        """Remove all chunks originating from a given PDF (used for re-ingest)."""
        self._ensure_loaded()
        keep_indices = [
            i
            for i, r in enumerate(self._records)
            if r.get("metadata", {}).get("source_pdf") != source_pdf
        ]
        if len(keep_indices) == len(self._records):
            return 0
        removed = len(self._records) - len(keep_indices)
        if keep_indices:
            self._embeddings = self._embeddings[keep_indices]
            self._records = [self._records[i] for i in keep_indices]
        else:
            self._embeddings = np.zeros((0, 0), dtype=np.float32)
            self._records = []
        self._id_to_idx = {r["chunk_id"]: i for i, r in enumerate(self._records)}
        self._persist()
        return removed

    def clear(self) -> None:
        """Drop the entire store (used by `ingest.py --rebuild`)."""
        self._ensure_loaded()
        self._embeddings = np.zeros((0, 0), dtype=np.float32)
        self._records = []
        self._id_to_idx = {}
        for p in (self._embeddings_path, self._records_path):
            if p.exists():
                p.unlink()
        logger.info("Vector store cleared.")

    # ----- Read path ---------------------------------------------------------

    def count(self) -> int:
        self._ensure_loaded()
        return len(self._records)

    def all_records(self) -> list[dict]:
        """Return every stored record (used by `ingest.py --stats`)."""
        self._ensure_loaded()
        return list(self._records)

    def query(
        self,
        query_text: str,
        top_k: int | None = None,
        domain: str | None = None,
    ) -> list[RetrievedChunk]:
        """Retrieve the top-k most similar records to `query_text`.

        If `domain` is set and not "general", filtering is applied so only
        chunks matching that domain (plus "constitutional" as a soft fallback,
        since constitutional principles cut across topics) are scored.
        """
        if not query_text.strip():
            return []
        self._ensure_loaded()
        if not self._records:
            logger.warning("Vector store is empty; run `python ingest.py` first.")
            return []

        k = top_k or self._settings.retrieval_top_k

        if domain and domain != "general":
            allowed = {domain, "constitutional"}
            mask = np.fromiter(
                (r["metadata"].get("domain") in allowed for r in self._records),
                dtype=bool,
                count=len(self._records),
            )
            if not mask.any():
                # Fall back to the whole index rather than returning empty.
                candidate_indices = np.arange(len(self._records))
                candidate_emb = self._embeddings
            else:
                candidate_indices = np.where(mask)[0]
                candidate_emb = self._embeddings[candidate_indices]
        else:
            candidate_indices = np.arange(len(self._records))
            candidate_emb = self._embeddings

        query_vec = self.embed([query_text])[0]
        # Cosine sim = dot product because both sides are L2-normalised.
        sims = candidate_emb @ query_vec  # shape (M,)

        actual_k = min(k, sims.shape[0])
        if actual_k <= 0:
            return []

        if actual_k < sims.shape[0]:
            top_local = np.argpartition(-sims, actual_k - 1)[:actual_k]
        else:
            top_local = np.arange(sims.shape[0])
        top_local = top_local[np.argsort(-sims[top_local])]

        out: list[RetrievedChunk] = []
        for local_i in top_local:
            global_i = int(candidate_indices[local_i])
            r = self._records[global_i]
            out.append(
                RetrievedChunk(
                    chunk_id=r["chunk_id"],
                    text=r["text"],
                    metadata=r["metadata"],
                    distance=float(1.0 - sims[local_i]),
                )
            )
        return out


_retriever_singleton: Retriever | None = None
_retriever_lock = threading.Lock()


def get_retriever() -> Retriever:
    """Return a process-wide Retriever singleton."""
    global _retriever_singleton
    if _retriever_singleton is None:
        with _retriever_lock:
            if _retriever_singleton is None:
                _retriever_singleton = Retriever()
    return _retriever_singleton
