"""PDF ingestion: parse Indian Act PDFs into section-aware chunks.

Strategy:
    1. Extract text per page with pdfplumber (preserves layout better than pypdf
       for the multi-column gazette format used by indiacode.nic.in).
    2. Detect section headings using a regex tuned for Indian legislative drafting
       ("Section 12.", "12.", "Sec. 12A.", etc.).
    3. Split the document at section boundaries; if a section is too long, split
       further with a token-aware sliding window so embedding context is preserved.
    4. Attach uniform metadata (act_name, section, domain, year, source_pdf) so
       downstream filtering by `where={"domain": "criminal"}` works in Chroma.

Filename convention (read by `derive_metadata`):
    <act_name>__<year>__<domain>.pdf
    e.g. "Bharatiya_Nyaya_Sanhita__2023__criminal.pdf"
If the convention isn't followed, sane defaults are used and a warning logged.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import pdfplumber

logger = logging.getLogger(__name__)

# Recognised legal domains. Keep this list aligned with classifier.py.
KNOWN_DOMAINS: frozenset[str] = frozenset(
    {
        "criminal",
        "consumer",
        "labour",
        "family",
        "cyber",
        "property",
        "constitutional",
        "tax",
        "general",
    }
)

# Matches: "Section 12.", "12.", "Sec 12A.", "Section 12-A —", "12A.—"
_SECTION_HEADING_RE = re.compile(
    r"^\s*(?:Section|Sec\.?)?\s*(\d{1,4}[A-Z]{0,3})\s*[.\-—–]\s*",
    re.IGNORECASE,
)

# Targets for chunk sizing (in characters; ~4 chars/token average for English).
_MAX_CHUNK_CHARS = 1800
_MIN_CHUNK_CHARS = 200
_OVERLAP_CHARS = 200


@dataclass(slots=True)
class Chunk:
    """A single retrievable unit produced by ingestion."""

    text: str
    metadata: dict[str, str | int]
    chunk_id: str

    def to_chroma(self) -> tuple[str, str, dict[str, str | int]]:
        """Return the (id, document, metadata) triple Chroma expects."""
        return self.chunk_id, self.text, self.metadata


@dataclass(slots=True)
class _DocMeta:
    act_name: str
    year: str
    domain: str
    source_pdf: str


@dataclass(slots=True)
class _RawSection:
    section: str
    text: str
    page_start: int
    extra: dict[str, str | int] = field(default_factory=dict)


def derive_metadata(pdf_path: Path) -> _DocMeta:
    """Parse `<act>__<year>__<domain>.pdf` filename convention.

    Falls back to filename stem + "general" if the convention is not followed.
    """
    stem = pdf_path.stem
    parts = stem.split("__")
    if len(parts) >= 3:
        act_name = parts[0].replace("_", " ").strip()
        year = parts[1].strip()
        domain = parts[2].strip().lower()
    else:
        logger.warning(
            "PDF '%s' does not follow `act__year__domain.pdf` convention; "
            "defaulting domain=general",
            pdf_path.name,
        )
        act_name = stem.replace("_", " ").strip()
        year = ""
        domain = "general"

    if domain not in KNOWN_DOMAINS:
        logger.warning("Unknown domain '%s' in %s; treating as 'general'", domain, pdf_path.name)
        domain = "general"

    return _DocMeta(
        act_name=act_name,
        year=year,
        domain=domain,
        source_pdf=pdf_path.name,
    )


def _extract_pages(pdf_path: Path) -> list[tuple[int, str]]:
    """Return [(page_number, text), ...] with empty pages skipped."""
    out: list[tuple[int, str]] = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            text = text.strip()
            if text:
                out.append((i, text))
    return out


def _split_into_sections(pages: list[tuple[int, str]]) -> list[_RawSection]:
    """Group lines under their nearest preceding section heading."""
    sections: list[_RawSection] = []
    current: _RawSection | None = None
    preamble_buffer: list[str] = []
    preamble_page: int = pages[0][0] if pages else 1

    for page_no, text in pages:
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                if current is not None:
                    current.text += "\n"
                continue

            heading = _SECTION_HEADING_RE.match(stripped)
            if heading:
                if current is not None:
                    sections.append(current)
                section_id = heading.group(1).upper()
                # Body text is whatever follows the heading on the same line.
                body = _SECTION_HEADING_RE.sub("", stripped, count=1)
                current = _RawSection(
                    section=section_id,
                    text=body + "\n",
                    page_start=page_no,
                )
            else:
                if current is None:
                    preamble_buffer.append(stripped)
                else:
                    current.text += stripped + "\n"

    if current is not None:
        sections.append(current)

    # Preserve preamble (definitions, preamble clauses) under a synthetic section.
    if preamble_buffer:
        sections.insert(
            0,
            _RawSection(
                section="PREAMBLE",
                text="\n".join(preamble_buffer),
                page_start=preamble_page,
            ),
        )
    return sections


def _sliding_window(text: str, max_chars: int, overlap: int) -> Iterator[str]:
    """Yield overlapping windows over `text`, never breaking mid-paragraph if avoidable."""
    if len(text) <= max_chars:
        yield text
        return

    start = 0
    n = len(text)
    while start < n:
        end = min(start + max_chars, n)
        # Prefer breaking at the last paragraph boundary inside the window.
        if end < n:
            soft_break = text.rfind("\n\n", start, end)
            if soft_break == -1 or soft_break - start < max_chars // 2:
                soft_break = text.rfind(". ", start, end)
            if soft_break != -1 and soft_break - start >= max_chars // 2:
                end = soft_break + 1
        yield text[start:end].strip()
        if end >= n:
            break
        start = max(end - overlap, start + 1)


def chunk_pdf(pdf_path: Path) -> list[Chunk]:
    """Convert one PDF into a list of `Chunk` objects ready for embedding."""
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    meta = derive_metadata(pdf_path)
    pages = _extract_pages(pdf_path)
    if not pages:
        logger.warning("No extractable text in %s", pdf_path.name)
        return []

    raw_sections = _split_into_sections(pages)
    chunks: list[Chunk] = []

    for raw in raw_sections:
        body = raw.text.strip()
        if len(body) < _MIN_CHUNK_CHARS and raw.section != "PREAMBLE":
            # Tiny sections (e.g. "Repealed.") still get one chunk to remain searchable.
            pieces = [body]
        else:
            pieces = list(_sliding_window(body, _MAX_CHUNK_CHARS, _OVERLAP_CHARS))

        for idx, piece in enumerate(pieces):
            if not piece:
                continue
            chunk_id = f"{meta.source_pdf}::sec_{raw.section}::part_{idx}"
            chunks.append(
                Chunk(
                    text=piece,
                    chunk_id=chunk_id,
                    metadata={
                        "act_name": meta.act_name,
                        "section": raw.section,
                        "domain": meta.domain,
                        "year": meta.year,
                        "source_pdf": meta.source_pdf,
                        "page_start": raw.page_start,
                    },
                )
            )

    logger.info("Ingested %s -> %d chunks", pdf_path.name, len(chunks))
    return chunks


def chunk_directory(data_dir: Path) -> Iterator[Chunk]:
    """Yield chunks from every PDF under `data_dir` (non-recursive by default)."""
    if not data_dir.exists():
        raise FileNotFoundError(data_dir)
    pdfs = sorted(data_dir.glob("*.pdf"))
    if not pdfs:
        logger.warning("No PDFs found in %s", data_dir)
    for pdf in pdfs:
        try:
            yield from chunk_pdf(pdf)
        except Exception as exc:  # pragma: no cover - corrupt PDFs are real
            logger.exception("Failed to ingest %s: %s", pdf.name, exc)
