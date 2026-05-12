"""FastAPI application: composes the RAG pipeline into HTTP routes.

Every route returns a structured JSON envelope. The QA, FIR, and document-analysis
endpoints additionally include a `pipeline_trace` block — that's what powers the
frontend's Pipeline Visualizer feature.

QA endpoint accepts optional `history` (prior conversation turns) and
`document_context` (a document being discussed), which lets the same pipeline
power follow-up chat in the Q&A, Strategy, and Document Analyzer pages.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from config import get_settings
from pipeline.classifier import ClassificationResult, classify
from pipeline.llm_caller import LLMConfigError, call_llm
from pipeline.postprocessor import PostprocessError, parse
from pipeline.prompt_builder import PromptMode, build_prompt
from pipeline.reranker import RerankedChunk, get_reranker
from pipeline.retriever import RetrievedChunk, get_retriever
from services.document_extractor import extract_text
from services.fir_pdf import render_fir_pdf

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("legalease")


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    settings = get_settings()
    settings.ensure_dirs()
    logger.info("LegalEase AI starting up. Chroma dir: %s", settings.chroma_dir)
    try:
        get_retriever()._get_model()  # noqa: SLF001 — intentional warmup
        get_reranker()._get_model()  # noqa: SLF001
        logger.info("Embedding + rerank models warmed.")
    except Exception as exc:  # pragma: no cover
        logger.warning("Model warmup skipped: %s", exc)
    yield
    logger.info("LegalEase AI shutting down.")


settings = get_settings()
app = FastAPI(
    title="LegalEase AI",
    description="Retrieval-Augmented Generation system for Indian law.",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    # Generous limit — the first turn's content can be a full QA / STRATEGY
    # answer, which occasionally runs long. Prompt builder truncates per-turn
    # again at 1500 chars before sending to the LLM.
    content: str = Field(..., max_length=20_000)


class QARequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000)
    language: Literal["en", "hi"] = "en"
    history: list[ChatTurn] = Field(default_factory=list)
    # Matches the cap in services/document_extractor._MAX_CHARS plus a small
    # buffer for safety (some pages may slightly exceed during OCR concatenation).
    document_context: str | None = Field(default=None, max_length=40_000)
    top_k_retrieve: int | None = Field(default=None, ge=1, le=50)
    top_k_rerank: int | None = Field(default=None, ge=1, le=20)


class FIRRequest(BaseModel):
    incident_description: str = Field(..., min_length=20, max_length=4000)
    complainant_name: str | None = Field(default=None, max_length=200)
    incident_location: str | None = Field(default=None, max_length=300)
    incident_datetime: str | None = Field(default=None, max_length=100)
    language: Literal["en", "hi"] = "en"


class PipelineTrace(BaseModel):
    query: str
    classification: dict[str, Any]
    retrieved_chunks: list[dict[str, Any]]
    reranked_chunks: list[dict[str, Any]]
    prompt_mode: str
    language: str
    model: str
    latency_ms: dict[str, float]


class StructuredEnvelope(BaseModel):
    ok: bool
    mode: str
    data: dict[str, Any]
    citations: list[dict[str, Any]]
    pipeline_trace: PipelineTrace


# ---------------------------------------------------------------------------
# Pipeline orchestration helper
# ---------------------------------------------------------------------------


async def _run_pipeline(
    *,
    query: str,
    mode: PromptMode,
    language: str,
    extras: dict | None = None,
    history: list[dict] | None = None,
    top_k_retrieve: int | None = None,
    top_k_rerank: int | None = None,
    max_output_tokens: int = 2048,
) -> StructuredEnvelope:
    timings: dict[str, float] = {}

    # 1. Classify
    t0 = time.perf_counter()
    cls: ClassificationResult = classify(query)
    timings["classify_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    # 2. Retrieve
    t0 = time.perf_counter()
    retriever = get_retriever()
    retrieved: list[RetrievedChunk] = retriever.query(
        query, top_k=top_k_retrieve, domain=cls.domain
    )
    timings["retrieve_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    # 3. Rerank
    t0 = time.perf_counter()
    reranker = get_reranker()
    reranked: list[RerankedChunk] = reranker.rerank(query, retrieved, top_k=top_k_rerank)
    timings["rerank_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    # 4. Build prompt
    t0 = time.perf_counter()
    prompt = build_prompt(
        query=query,
        mode=mode,
        chunks=reranked,
        language=language,
        extras=extras,
        history=history,
    )
    timings["prompt_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    # 5. Call LLM
    t0 = time.perf_counter()
    try:
        llm_result = await call_llm(prompt, max_output_tokens=max_output_tokens)
    except LLMConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("LLM call failed")
        raise HTTPException(status_code=502, detail=f"Upstream LLM failure: {exc}") from exc
    timings["llm_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    # 6. Postprocess
    t0 = time.perf_counter()
    try:
        structured = parse(llm_result.text, mode=mode, chunks=reranked)
    except PostprocessError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    timings["postprocess_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    trace = PipelineTrace(
        query=query,
        classification={
            "domain": cls.domain,
            "confidence": cls.confidence,
            "scores": cls.scores,
            "matched_keywords": cls.matched_keywords,
        },
        retrieved_chunks=[
            {
                "chunk_id": c.chunk_id,
                "similarity": c.similarity,
                "metadata": c.metadata,
                "preview": c.text[:240],
            }
            for c in retrieved
        ],
        reranked_chunks=[c.to_payload() for c in reranked],
        prompt_mode=mode.value,
        language=language,
        model=llm_result.model,
        latency_ms=timings,
    )

    return StructuredEnvelope(
        ok=True,
        mode=mode.value,
        data=structured.data,
        citations=structured.citations,
        pipeline_trace=trace,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/api/health")
async def health() -> dict[str, Any]:
    retriever = get_retriever()
    return {
        "ok": True,
        "service": "LegalEase AI",
        "version": app.version,
        "indexed_chunks": retriever.count(),
        "model": settings.gemini_model,
        "embedding_model": settings.embedding_model,
        "reranker_model": settings.reranker_model,
    }


@app.post("/api/qa", response_model=StructuredEnvelope)
async def qa(req: QARequest) -> StructuredEnvelope:
    """
    Mode selection:
      - First turn, no document context → QA mode (full structured response).
      - Any follow-up (history present) → CHAT mode (concise conversational reply).
      - Any turn with a document being discussed → CHAT mode (the user has
        already seen the structured analysis; follow-ups should be concise).

    CHAT mode also uses a tighter output token budget so the LLM returns
    faster (2-5 sentence answers don't need 2048 tokens of headroom).
    """
    history = [t.model_dump() for t in req.history]
    extras = {"document_context": req.document_context} if req.document_context else None

    if req.document_context or history:
        mode = PromptMode.CHAT
        max_tokens = 1024  # concise chat reply — faster round-trip
    else:
        mode = PromptMode.QA
        max_tokens = 2048

    return await _run_pipeline(
        query=req.query,
        mode=mode,
        language=req.language,
        extras=extras,
        history=history,
        top_k_retrieve=req.top_k_retrieve,
        top_k_rerank=req.top_k_rerank,
        max_output_tokens=max_tokens,
    )


@app.post("/api/strategy", response_model=StructuredEnvelope)
async def strategy(req: QARequest) -> StructuredEnvelope:
    """First turn returns a phased STRATEGY plan; follow-ups switch to CHAT."""
    history = [t.model_dump() for t in req.history]
    mode = PromptMode.CHAT if history else PromptMode.STRATEGY
    return await _run_pipeline(
        query=req.query,
        mode=mode,
        language=req.language,
        history=history,
        max_output_tokens=3072 if mode is PromptMode.STRATEGY else 2048,
    )


@app.post("/api/fir", response_model=StructuredEnvelope)
async def fir(req: FIRRequest) -> StructuredEnvelope:
    extras = {
        "complainant_name": req.complainant_name or "",
        "incident_location": req.incident_location or "",
        "incident_datetime": req.incident_datetime or "",
    }
    return await _run_pipeline(
        query=req.incident_description,
        mode=PromptMode.FIR,
        language=req.language,
        extras=extras,
    )


@app.post("/api/fir/pdf")
async def fir_pdf(req: FIRRequest) -> Response:
    envelope = await fir(req)
    pdf_bytes = render_fir_pdf(envelope.data, complainant_name=req.complainant_name)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="legalease_fir_draft.pdf"',
        },
    )


@app.post("/api/analyze-document", response_model=StructuredEnvelope)
async def analyze_document(
    file: UploadFile = File(...),
    concern: str = Form(""),
    language: Literal["en", "hi"] = Form("en"),
) -> StructuredEnvelope:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        document_text = extract_text(file.filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Document extraction failed")
        raise HTTPException(status_code=400, detail=f"Could not read document: {exc}") from exc

    if not document_text.strip():
        raise HTTPException(status_code=400, detail="No extractable text in document.")

    # Use the document text as the retrieval query, supplemented by user concern.
    retrieval_query = (concern + "\n\n" + document_text[:2000]).strip()

    envelope = await _run_pipeline(
        query=retrieval_query,
        mode=PromptMode.DOCUMENT_ANALYSIS,
        language=language,
        extras={"document_text": document_text, "concern": concern},
        # 8192 token budget — the exhaustive "list EVERY clause and EVERY risk"
        # prompt can produce 4-6k tokens of output for a substantial contract.
        # Hitting the cap mid-array is the #1 cause of "LLM did not return JSON"
        # errors, which the postprocessor now also recovers from but it's
        # better to not hit it in the first place.
        max_output_tokens=8192,
    )

    # Stash the extracted document text on the envelope so the frontend can
    # use it as `document_context` for follow-up chat questions.
    envelope.data["_document_text"] = document_text
    return envelope


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def run() -> None:
    """Used by `python -m main` or by `uvicorn main:app`."""
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    run()
