"""Gemini API wrapper.

This is the *only* module in the project that talks to an external LLM. It
exposes a narrow async interface so the rest of the pipeline doesn't depend on
SDK-specific types.

Uses `google-genai`, the unified SDK that replaces the legacy `google-generativeai`.

`GEMINI_MODEL` may be a single model name OR a comma-separated priority list.
On a 429 (quota exhausted) for one model, the wrapper automatically falls
through to the next model in the list. The model that ultimately answers is
returned in `LLMResult.model` so the pipeline trace stays honest.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from google import genai
from google.genai import types

from config import get_settings
from pipeline.prompt_builder import BuiltPrompt

logger = logging.getLogger(__name__)


class LLMConfigError(RuntimeError):
    """Raised when the Gemini client is mis-configured (e.g. missing API key)."""


class LLMCallError(RuntimeError):
    """Raised when every model in the priority list fails."""


@dataclass(slots=True)
class LLMResult:
    text: str
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None


_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is not None:
        return _client
    settings = get_settings()
    if not settings.gemini_api_key:
        raise LLMConfigError(
            "GEMINI_API_KEY is not set. Add it to backend/.env. "
            "Get a key from https://aistudio.google.com/app/apikey"
        )
    _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def _is_quota_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "429" in msg or "resource_exhausted" in msg or "quota" in msg


async def call_llm(
    prompt: BuiltPrompt,
    *,
    temperature: float = 0.2,
    max_output_tokens: int = 2048,
    response_mime_type: str = "application/json",
) -> LLMResult:
    """Synthesise a response from a `BuiltPrompt`.

    Iterates through the comma-separated `GEMINI_MODEL` priority list and falls
    through to the next model on quota / 429 errors. The first model to return
    a non-empty response wins.
    """
    settings = get_settings()
    client = _get_client()

    models = [m.strip() for m in settings.gemini_model.split(",") if m.strip()]
    if not models:
        raise LLMConfigError("No Gemini model configured (GEMINI_MODEL is empty)")

    config = types.GenerateContentConfig(
        system_instruction=prompt.system,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        response_mime_type=response_mime_type,
    )

    last_exc: Exception | None = None
    for idx, model_name in enumerate(models):
        def _sync_call(mn: str = model_name) -> types.GenerateContentResponse:
            return client.models.generate_content(
                model=mn,
                contents=prompt.user,
                config=config,
            )

        try:
            response = await asyncio.to_thread(_sync_call)
            text = (response.text or "").strip()
            if not text:
                raise LLMCallError(f"Empty response from {model_name}")

            usage = getattr(response, "usage_metadata", None)
            if idx > 0:
                logger.info(
                    "Fell through to model #%d (%s) after %d quota failure(s)",
                    idx + 1,
                    model_name,
                    idx,
                )
            return LLMResult(
                text=text,
                model=model_name,
                prompt_tokens=getattr(usage, "prompt_token_count", None) if usage else None,
                completion_tokens=(
                    getattr(usage, "candidates_token_count", None) if usage else None
                ),
            )
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if _is_quota_error(exc):
                logger.warning(
                    "Model %s quota exhausted; trying next in priority list", model_name
                )
            else:
                logger.warning(
                    "Model %s failed (%s); trying next", model_name, exc
                )
            continue

    raise LLMCallError(
        f"All {len(models)} models exhausted; last error: {last_exc}"
    ) from last_exc
