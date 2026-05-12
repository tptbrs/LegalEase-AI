"""Structured-response parser.

The LLM is told to emit JSON, but real-world models occasionally wrap output in
```json ... ``` fences, prepend an explanatory sentence, or truncate. This module
takes the raw LLM text and:

  1. Strips common wrappers (markdown fences, leading/trailing prose).
  2. Attempts `json.loads`. Falls back to a brace-balance recovery pass.
  3. Validates against the mode's expected top-level keys.
  4. Resolves [#cite] tags against the actual retrieved chunks so the frontend
     gets fully-hydrated citation objects.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from pipeline.prompt_builder import PromptMode
from pipeline.reranker import RerankedChunk

logger = logging.getLogger(__name__)


class PostprocessError(RuntimeError):
    pass


@dataclass(slots=True)
class StructuredResponse:
    mode: PromptMode
    data: dict[str, Any]
    citations: list[dict[str, Any]]
    raw: str


_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.MULTILINE)
# Trailing comma before a closing brace/bracket — common LLM mistake.
_TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")
# Smart / curly quotes that some models use instead of ASCII quotes.
_SMART_QUOTES = {
    "“": '"',
    "”": '"',
    "„": '"',
    "‘": "'",
    "’": "'",
}


_REQUIRED_KEYS: dict[PromptMode, set[str]] = {
    PromptMode.QA: {"answer"},
    PromptMode.CHAT: {"answer"},
    PromptMode.STRATEGY: {"phases"},
    PromptMode.FIR: {"incident_narrative", "applicable_sections"},
    PromptMode.DOCUMENT_ANALYSIS: {"summary", "key_clauses", "risks"},
}


def _normalise_quotes(text: str) -> str:
    out = text
    for fancy, ascii_quote in _SMART_QUOTES.items():
        out = out.replace(fancy, ascii_quote)
    return out


def _strip_wrappers(text: str) -> str:
    cleaned = _FENCE_RE.sub("", text).strip()
    cleaned = _normalise_quotes(cleaned)
    # Drop everything before the first '{' and after the matching last '}'.
    first = cleaned.find("{")
    last = cleaned.rfind("}")
    if first == -1 or last == -1 or last < first:
        return cleaned
    return cleaned[first : last + 1]


def _balanced_recover(text: str) -> str | None:
    """Heuristic: scan for the first balanced JSON object in `text`."""
    text = _normalise_quotes(text)
    depth = 0
    start: int | None = None
    in_string = False
    escape = False

    for i, ch in enumerate(text):
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                return text[start : i + 1]
    return None


def _repair_truncated(text: str) -> str | None:
    """If JSON was cut off mid-array (max_output_tokens hit), try to close it.

    We count unclosed `{` and `[` brackets and append matching closers. This
    lets us recover at least a partial document analysis instead of failing
    the whole request.
    """
    text = _normalise_quotes(text)
    first = text.find("{")
    if first == -1:
        return None
    candidate = text[first:]

    depth_curly = 0
    depth_square = 0
    in_string = False
    escape = False
    last_complete = -1

    for i, ch in enumerate(candidate):
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth_curly += 1
        elif ch == "}":
            depth_curly -= 1
        elif ch == "[":
            depth_square += 1
        elif ch == "]":
            depth_square -= 1
        if depth_curly == 0 and depth_square == 0:
            last_complete = i

    # If we already have a complete object somewhere, use it.
    if last_complete != -1:
        return candidate[: last_complete + 1]

    # Otherwise close the unclosed brackets.
    # Strip trailing comma/whitespace before appending closers.
    truncated = candidate.rstrip().rstrip(",")
    # If we ended mid-string, close it.
    if in_string:
        truncated = truncated + '"'
    closers = "]" * max(depth_square, 0) + "}" * max(depth_curly, 0)
    return truncated + closers if closers else None


def _try_load(text: str) -> dict[str, Any] | None:
    try:
        result = json.loads(text)
        return result if isinstance(result, dict) else None
    except json.JSONDecodeError:
        # One more attempt with trailing-comma scrub — Gemini occasionally
        # leaves a comma before a closing bracket.
        scrubbed = _TRAILING_COMMA_RE.sub(r"\1", text)
        try:
            result = json.loads(scrubbed)
            return result if isinstance(result, dict) else None
        except json.JSONDecodeError:
            return None


def _hydrate_citations(
    data: dict[str, Any],
    chunks: list[RerankedChunk],
) -> list[dict[str, Any]]:
    """Walk the response, collecting every `cite` integer and resolving it.

    `cite` is the [#n] index in the prompt's CONTEXT block, which is 1-based.
    """
    cite_indices: set[int] = set()

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "cite" and isinstance(value, int):
                    cite_indices.add(value)
                else:
                    _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(data)

    citations: list[dict[str, Any]] = []
    for idx in sorted(cite_indices):
        pos = idx - 1
        if 0 <= pos < len(chunks):
            chunk = chunks[pos]
            citations.append(
                {
                    "cite": idx,
                    "act_name": chunk.metadata.get("act_name"),
                    "section": chunk.metadata.get("section"),
                    "year": chunk.metadata.get("year"),
                    "source_pdf": chunk.metadata.get("source_pdf"),
                    "snippet": chunk.text[:400],
                }
            )
    return citations


def parse(
    raw_text: str,
    mode: PromptMode,
    chunks: list[RerankedChunk],
) -> StructuredResponse:
    """Parse the LLM's raw output into a typed `StructuredResponse`."""
    if not raw_text:
        raise PostprocessError("LLM returned empty text")

    cleaned = _strip_wrappers(raw_text)
    parsed = _try_load(cleaned)

    if parsed is None:
        recovered = _balanced_recover(raw_text)
        if recovered is not None:
            parsed = _try_load(recovered)

    if parsed is None:
        # Last-resort: the JSON may have been truncated by max_output_tokens.
        # Close unclosed brackets and try again.
        repaired = _repair_truncated(raw_text)
        if repaired is not None:
            parsed = _try_load(repaired)
            if parsed is not None:
                logger.warning(
                    "LLM output was truncated; recovered partial JSON for mode=%s",
                    mode.value,
                )

    if parsed is None:
        logger.error(
            "Could not parse LLM output as JSON. Mode=%s. First 400 chars: %s",
            mode.value,
            raw_text[:400],
        )
        raise PostprocessError(
            "The AI returned an incomplete response. "
            "This usually means the document was very large or the model output "
            "was cut short. Try a shorter document or a more specific question."
        )

    required = _REQUIRED_KEYS.get(mode, set())
    missing = required - set(parsed.keys())
    if missing:
        logger.warning("LLM output is missing required keys for mode=%s: %s", mode.value, missing)
        # Don't reject — surface what we have. The frontend can render partial.

    citations = _hydrate_citations(parsed, chunks)
    return StructuredResponse(
        mode=mode,
        data=parsed,
        citations=citations,
        raw=raw_text,
    )
