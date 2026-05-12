"""Extract text from uploaded user documents.

Supports:
  - PDFs with an embedded text layer  — fast path via pdfplumber.
  - Scanned PDFs (image-only pages)   — OCR fallback via EasyOCR + PyMuPDF.
  - Image files (.jpg, .jpeg, .png)   — direct OCR via EasyOCR.
  - Plain text (.txt, .md)            — UTF-8 decode.

Heavy OCR dependencies are imported lazily, so users who only ever upload
text-layered PDFs never pay the import cost. The EasyOCR reader is also
created lazily and cached at module level: first OCR call takes a few
seconds (model load + one-time model download from HuggingFace if missing),
subsequent OCR calls are fast.
"""

from __future__ import annotations

import io
import logging
import threading
from typing import Any

import pdfplumber

logger = logging.getLogger(__name__)

_MAX_CHARS = 30_000
# If pdfplumber returns this little text from the whole document, assume
# the PDF is scanned and try OCR.
_OCR_TRIGGER_TOTAL_CHARS = 500
# DPI for rendering each PDF page to an image before OCR. 150 is a good
# balance between OCR accuracy and speed/memory.
_OCR_RENDER_DPI = 150

_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff")
_PDF_EXTS = (".pdf",)
_TEXT_EXTS = (".txt", ".md")

_ocr_reader: Any | None = None
_ocr_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def extract_text(filename: str, content: bytes) -> str:
    """Return the document's text. Routes by file extension."""
    name = filename.lower()
    if name.endswith(_PDF_EXTS):
        return _extract_pdf(content)
    if name.endswith(_TEXT_EXTS):
        return content.decode("utf-8", errors="replace")[:_MAX_CHARS].strip()
    if name.endswith(_IMAGE_EXTS):
        text = _ocr_image_bytes(content)
        if not text:
            raise ValueError(
                "No text could be recognised in the uploaded image. "
                "Try a higher-quality scan or photograph."
            )
        return text
    raise ValueError(
        f"Unsupported file type: {filename}. "
        "Upload a .pdf, .txt, .md, .jpg, .jpeg, or .png."
    )


# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------


def _extract_pdf(content: bytes) -> str:
    """Try pdfplumber first; fall back to OCR if the PDF appears scanned."""
    pieces: list[str] = []
    total = 0

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            text = (page.extract_text() or "").strip()
            if not text:
                continue
            if total + len(text) > _MAX_CHARS:
                pieces.append(text[: _MAX_CHARS - total])
                total = _MAX_CHARS
                break
            pieces.append(text)
            total += len(text)

    extracted = "\n\n".join(pieces).strip()

    if total >= _OCR_TRIGGER_TOTAL_CHARS:
        # Text layer was rich enough — no OCR needed.
        return extracted

    logger.info(
        "PDF has only %d chars of extractable text across %d pages; running OCR fallback",
        total,
        page_count,
    )

    try:
        ocr_text = _ocr_pdf_bytes(content)
    except RuntimeError as exc:
        # OCR libraries not installed — report what we got and tell the user.
        if extracted:
            return extracted
        raise ValueError(
            "This PDF appears to be scanned (no extractable text layer), "
            "and OCR is not available on the server. "
            f"To enable OCR for scanned documents, install: {exc}"
        ) from exc

    # Prefer whichever yielded more content.
    if ocr_text and len(ocr_text) > len(extracted):
        logger.info("OCR succeeded: %d chars extracted from scanned PDF", len(ocr_text))
        return ocr_text
    return extracted


# ---------------------------------------------------------------------------
# OCR (lazy)
# ---------------------------------------------------------------------------


def _get_ocr_reader() -> Any:
    """Return a singleton EasyOCR Reader covering English + Hindi.

    Raises RuntimeError with an installation hint if easyocr isn't available.
    """
    global _ocr_reader
    if _ocr_reader is not None:
        return _ocr_reader

    with _ocr_lock:
        if _ocr_reader is not None:
            return _ocr_reader
        try:
            import easyocr  # type: ignore
        except ImportError as exc:
            raise RuntimeError("`pip install easyocr pymupdf`") from exc

        logger.info("Initialising EasyOCR reader (English + Hindi). First time may download ~100 MB of model weights.")
        _ocr_reader = easyocr.Reader(["en", "hi"], gpu=False, verbose=False)
        logger.info("EasyOCR ready.")
        return _ocr_reader


def _ocr_pdf_bytes(content: bytes) -> str:
    """Render each PDF page to an image and OCR it with EasyOCR."""
    reader = _get_ocr_reader()

    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise RuntimeError("`pip install pymupdf`") from exc

    try:
        import numpy as np
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("`pip install Pillow numpy`") from exc

    pieces: list[str] = []
    total = 0
    page_count = 0

    doc = fitz.open(stream=content, filetype="pdf")
    try:
        page_count = len(doc)
        for i in range(page_count):
            if total >= _MAX_CHARS:
                break
            page = doc[i]
            pix = page.get_pixmap(dpi=_OCR_RENDER_DPI, alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            img_arr = np.array(img)

            results = reader.readtext(img_arr, detail=0, paragraph=True)
            page_text = "\n".join(results).strip()

            if not page_text:
                continue
            if total + len(page_text) > _MAX_CHARS:
                pieces.append(page_text[: _MAX_CHARS - total])
                break
            pieces.append(page_text)
            total += len(page_text)
    finally:
        doc.close()

    return "\n\n".join(pieces).strip()


def _ocr_image_bytes(content: bytes) -> str:
    """OCR a single image (uploaded photo or scanned page)."""
    reader = _get_ocr_reader()

    try:
        import numpy as np
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("`pip install Pillow numpy`") from exc

    img = Image.open(io.BytesIO(content)).convert("RGB")
    img_arr = np.array(img)
    results = reader.readtext(img_arr, detail=0, paragraph=True)
    return "\n".join(results).strip()[:_MAX_CHARS]
