"""CLI entrypoint for ingesting Indian Act PDFs into ChromaDB.

Usage (from backend/ directory):

    python ingest.py                 # ingest every new/changed PDF in data/acts
    python ingest.py --rebuild       # delete the collection and re-ingest everything
    python ingest.py --file foo.pdf  # ingest a single PDF (path relative to data/acts)
    python ingest.py --stats         # print indexed-chunk counts per Act

Filename convention required for proper metadata:
    <act_name>__<year>__<domain>.pdf
    e.g. Bharatiya_Nyaya_Sanhita__2023__criminal.pdf
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from tqdm import tqdm

from config import get_settings
from pipeline.ingestion import chunk_pdf
from pipeline.retriever import get_retriever

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ingest")


def _ingest_one(pdf_path: Path) -> int:
    retriever = get_retriever()
    chunks = chunk_pdf(pdf_path)
    if not chunks:
        logger.warning("No chunks produced for %s", pdf_path.name)
        return 0
    # Replace any prior chunks from this PDF so re-ingest is idempotent.
    retriever.delete_by_source(pdf_path.name)
    return retriever.add(chunks)


def _ingest_all(data_dir: Path) -> int:
    pdfs = sorted(data_dir.glob("*.pdf"))
    if not pdfs:
        logger.warning("No PDFs in %s. Drop your Indian Act PDFs there.", data_dir)
        return 0
    total = 0
    for pdf in tqdm(pdfs, desc="Ingesting PDFs", unit="pdf"):
        total += _ingest_one(pdf)
    return total


def _print_stats() -> None:
    retriever = get_retriever()
    total = retriever.count()
    print(f"Total indexed chunks: {total}")
    if total == 0:
        return

    counts: dict[str, int] = {}
    domains: dict[str, int] = {}
    for record in retriever.all_records():
        meta = record.get("metadata", {})
        src = str(meta.get("source_pdf", "?"))
        dom = str(meta.get("domain", "?"))
        counts[src] = counts.get(src, 0) + 1
        domains[dom] = domains.get(dom, 0) + 1

    print("\nChunks per source PDF:")
    for src, n in sorted(counts.items()):
        print(f"  {n:>5}  {src}")

    print("\nChunks per domain:")
    for dom, n in sorted(domains.items(), key=lambda kv: -kv[1]):
        print(f"  {n:>5}  {dom}")


def _rebuild() -> None:
    retriever = get_retriever()
    retriever.clear()
    logger.info("Vector store cleared; ready for fresh ingest.")


def main() -> int:
    parser = argparse.ArgumentParser(description="LegalEase AI ingest CLI")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Override the configured data directory (default: backend/data/acts)",
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Ingest a single PDF (filename relative to data dir, or absolute path)",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Drop the collection before ingesting (full reindex)",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print collection statistics and exit",
    )
    args = parser.parse_args()

    settings = get_settings()
    settings.ensure_dirs()
    data_dir = (args.data_dir or settings.data_dir).resolve()

    if args.stats:
        _print_stats()
        return 0

    if args.rebuild:
        _rebuild()

    if args.file:
        candidate = Path(args.file)
        if not candidate.is_absolute():
            candidate = data_dir / args.file
        if not candidate.exists():
            print(f"PDF not found: {candidate}", file=sys.stderr)
            return 1
        n = _ingest_one(candidate)
        print(f"Ingested {n} chunks from {candidate.name}")
        return 0

    n = _ingest_all(data_dir)
    print(f"Ingested {n} chunks total. Index size: {get_retriever().count()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
