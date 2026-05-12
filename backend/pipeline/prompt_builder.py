"""Dynamic prompt builder.

We support multiple `PromptMode`s, one per product feature. Each mode produces
a distinct system + user prompt template tuned for that task. All modes share:

  * A common safety preamble ("you are not a substitute for a licensed advocate").
  * A JSON output contract — the LLM is told to produce a single JSON object
    matching a strict schema. The postprocessor parses that.
  * A context block enumerating the retrieved sections with [#cite] tags so the
    model is forced to ground its answer in retrieved law.
  * Conversational history support — prior user/assistant turns are injected
    so follow-up questions stay coherent.
  * Strong language-of-output enforcement — the requested language instruction
    appears in BOTH the system prompt and the final user reminder so that
    Gemini's JSON mode never silently drops it.

Public surface:
    - PromptMode (enum)
    - BuiltPrompt (system + user + mode + schema_hint)
    - build_prompt(query, mode, chunks, language="en", extras=None, history=None)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from pipeline.reranker import RerankedChunk


class PromptMode(str, Enum):
    QA = "qa"
    CHAT = "chat"
    STRATEGY = "strategy"
    FIR = "fir"
    DOCUMENT_ANALYSIS = "document_analysis"


@dataclass(slots=True)
class BuiltPrompt:
    system: str
    user: str
    mode: PromptMode
    language: str
    schema_hint: dict


_DISCLAIMER = (
    "This system provides legal information for educational purposes only. "
    "It is not a substitute for advice from a licensed advocate. "
    "Always consult a qualified legal professional for your specific case."
)

_BASE_SYSTEM = (
    "You are LegalEase AI, an applied NLP system specialising in Indian law. "
    "You answer ONLY using the retrieved legal sections supplied in the CONTEXT. "
    "If the context is insufficient, say so plainly — do not fabricate sections "
    "or invent statute numbers. Cite every legal claim with the [#n] tag of the "
    "context block you used."
)

_LANGUAGE_INSTRUCTIONS = {
    "en": (
        "RESPONSE LANGUAGE: English. "
        "Every string value in your JSON output (answer, summary, title, "
        "description, narrative, explanation, recommendations, warnings, etc.) "
        "MUST be in clear, formal Indian English."
    ),
    "hi": (
        "RESPONSE LANGUAGE: Hindi (Devanagari script). "
        "Every string value in your JSON output (answer, summary, title, "
        "description, narrative, explanation, recommendations, warnings, etc.) "
        "MUST be written in Hindi using Devanagari script — not Romanised Hindi. "
        "EXCEPTIONS that stay in English: "
        "(1) Names of statutes such as 'Indian Penal Code', 'Bharatiya Nyaya Sanhita', "
        "'Consumer Protection Act'. (2) Section numbers (e.g. 'Section 302' stays as is). "
        "Everything else — every sentence, every explanation, every recommendation — "
        "must be in Hindi Devanagari."
    ),
}


def _format_context_block(chunks: list[RerankedChunk]) -> str:
    if not chunks:
        return "CONTEXT: (no relevant sections retrieved)\n"
    lines: list[str] = ["CONTEXT (retrieved Indian legal sections):"]
    for i, c in enumerate(chunks, start=1):
        meta = c.metadata
        header = (
            f"[#{i}] {meta.get('act_name', 'Unknown Act')} "
            f"— Section {meta.get('section', '?')} "
            f"({meta.get('year', '')})"
        ).strip()
        lines.append(header)
        lines.append(c.text.strip())
        lines.append("")
    return "\n".join(lines)


def _format_history(history: list[dict] | None) -> str:
    """Render prior conversation turns into a single text block."""
    if not history:
        return ""
    lines = ["PREVIOUS CONVERSATION:"]
    for turn in history[-8:]:  # cap to last 8 turns to keep prompt manageable
        role = turn.get("role", "user").lower()
        content = (turn.get("content") or "").strip()
        if not content:
            continue
        label = "Assistant" if role == "assistant" else "User"
        # Truncate any single turn to keep total prompt size bounded.
        if len(content) > 1500:
            content = content[:1500] + "…"
        lines.append(f"{label}: {content}")
        lines.append("")
    return "\n".join(lines)


# --- Schemas (also returned to the frontend so the UI can render fields) -----

_QA_SCHEMA = {
    "answer": "string — direct, plain-language answer in the requested language",
    "key_provisions": [
        {
            "act_name": "string",
            "section": "string",
            "summary": "string",
            "cite": "integer — the [#n] tag from CONTEXT this provision came from",
        }
    ],
    "recommended_actions": ["string — concrete next step the user can take"],
    "warnings": ["string — risks, time-limits, or jurisdictional caveats"],
}

_CHAT_SCHEMA = {
    "answer": (
        "string — a concise, conversational answer of 2 to 5 sentences. "
        "Match the tone of a chat reply, not a formal report. Reference prior "
        "conversation context naturally."
    ),
    "citations": [
        {
            "cite": "integer — the [#n] tag from CONTEXT if you referenced a specific section",
            "note": "string | null — optional one-line note about why this section is relevant",
        }
    ],
}

_STRATEGY_SCHEMA = {
    "overview": (
        "string — 2 to 3 sentence neutral assessment of the user's situation and "
        "the legal options at a high level"
    ),
    "domain": "string — primary legal domain (criminal, consumer, labour, family, etc.)",
    "phases": [
        {
            "phase_number": "integer — 1, 2, 3, …",
            "title": "string — short label for this phase",
            "description": "string — what the user should do in this phase, 1-3 sentences",
            "expected_duration": "string — e.g. '1-2 weeks', '3 months'",
            "estimated_cost": "string — qualitative like 'minimal', 'INR 5,000-20,000', 'high'",
            "statutory_basis": [
                {"act_name": "string", "section": "string", "cite": "integer"}
            ],
            "risks_if_skipped": "string — what could go wrong if this phase is omitted",
        }
    ],
    "critical_deadlines": [
        "string — time-bound steps, e.g. 'File FIR within 24 hours of incident'"
    ],
    "evidence_to_preserve": ["string"],
    "warnings": ["string"],
}

_FIR_SCHEMA = {
    "fir_title": "string",
    "complainant_summary": "string — paraphrased one-paragraph statement",
    "incident_narrative": "string — formal first-person narrative suitable for an FIR",
    "applicable_sections": [
        {
            "act_name": "string (e.g. 'Bharatiya Nyaya Sanhita, 2023')",
            "section": "string",
            "offence": "string — short label of the offence",
            "cite": "integer",
        }
    ],
    "police_station_guidance": "string — which police station to approach and why",
    "evidence_to_collect": ["string"],
    "warnings": ["string"],
}

_DOC_ANALYSIS_SCHEMA = {
    "document_type": "string — e.g. 'Rental Agreement', 'Legal Notice', 'Employment Contract'",
    "summary": (
        "string — a comprehensive 6 to 10 sentence summary covering the document's "
        "purpose, the parties involved, key obligations, timelines, and overall nature"
    ),
    "key_clauses": [
        {
            "clause_title": "string",
            "clause_text": "string — short verbatim or near-verbatim quote",
            "interpretation": "string",
        }
    ],
    "risks": [
        {
            "severity": "string — one of 'low', 'medium', 'high'",
            "issue": "string",
            "explanation": "string",
            "supporting_law_cite": "integer | null",
        }
    ],
    "recommendations": ["string"],
    "warnings": ["string"],
}

_SCHEMAS: dict[PromptMode, dict] = {
    PromptMode.QA: _QA_SCHEMA,
    PromptMode.CHAT: _CHAT_SCHEMA,
    PromptMode.STRATEGY: _STRATEGY_SCHEMA,
    PromptMode.FIR: _FIR_SCHEMA,
    PromptMode.DOCUMENT_ANALYSIS: _DOC_ANALYSIS_SCHEMA,
}


def _user_block(
    query: str,
    mode: PromptMode,
    extras: dict | None,
    history: list[dict] | None,
) -> str:
    extras = extras or {}
    parts: list[str] = []

    # 1. Optional document context (used by document follow-up chat).
    doc_context = extras.get("document_context") if extras else None
    if doc_context:
        doc = doc_context[:8000]
        parts.append(
            f"DOCUMENT BEING DISCUSSED (excerpt):\n{doc}\n"
        )

    # 2. Optional prior conversation.
    history_block = _format_history(history)
    if history_block:
        parts.append(history_block)

    # 3. Mode-specific task framing.
    if mode is PromptMode.QA:
        parts.append(f"USER QUESTION:\n{query}\n")

    elif mode is PromptMode.CHAT:
        parts.append(
            "TASK: You are continuing a legal conversation. Answer the user's "
            "follow-up question BRIEFLY and DIRECTLY (typically 2 to 5 sentences). "
            "Match the tone of a chat reply, not a formal report. Reference the "
            "prior conversation naturally. If a DOCUMENT BEING DISCUSSED is "
            "supplied above, ground your answer in its text plus any relevant "
            "CONTEXT sections. Only add citations when you reference a specific "
            "statutory section — do not pad with citations for general advice.\n\n"
            f"USER QUESTION:\n{query}\n"
        )

    elif mode is PromptMode.STRATEGY:
        parts.append(
            "TASK: Build a phased legal action strategy for the situation below. "
            "Do not just answer 'what does the law say'; design an ordered plan "
            "of phases the user should execute.\n\n"
            "For each phase provide: a clear title, a 1-3 sentence description of "
            "what to do, an expected duration, a qualitative cost estimate, the "
            "specific statutory hooks (with [#n] citations from CONTEXT), and "
            "the risks of skipping that phase. Order phases from cheapest / "
            "fastest first to litigation / costly last. List critical time-bound "
            "steps (limitation periods, FIR within 24 hours, statutory notice "
            "deadlines) under critical_deadlines. List artefacts the user must "
            "preserve under evidence_to_preserve.\n\n"
            f"SITUATION:\n{query}\n"
        )

    elif mode is PromptMode.FIR:
        complainant = extras.get("complainant_name", "Complainant")
        location = extras.get("incident_location", "[location not provided]")
        when = extras.get("incident_datetime", "[date/time not provided]")
        parts.append(
            "TASK: Draft a formal FIR (First Information Report) for an Indian "
            "police station based on the incident description below. Use BNS 2023 "
            "section numbers where the context provides them; if only IPC sections "
            "are available, cite IPC and note the BNS equivalent if known.\n\n"
            f"Complainant name: {complainant}\n"
            f"Location of incident: {location}\n"
            f"Date/time of incident: {when}\n"
            f"Incident description (verbatim from user):\n{query}\n"
        )

    elif mode is PromptMode.DOCUMENT_ANALYSIS:
        doc_text = extras.get("document_text", "")
        parts.append(
            "TASK: Analyse the legal document below THOROUGHLY and EXHAUSTIVELY.\n"
            "\n"
            "1. Identify the document type (e.g. Rental Agreement, Employment Contract, "
            "Legal Notice, Service Agreement).\n"
            "\n"
            "2. Write a COMPREHENSIVE summary of 6 to 10 full sentences covering: "
            "the document's purpose, the parties involved, the principal obligations "
            "of each party, key timelines or duration, payment/consideration terms, "
            "and the overall nature and tone of the document.\n"
            "\n"
            "3. Extract EVERY key clause present in the document — every clause that "
            "creates an obligation, grants a right, imposes a restriction, or sets a "
            "material term. Do NOT stop at 3 or 4 clauses. Continue listing until you "
            "have covered every materially significant clause in the document.\n"
            "\n"
            "4. Identify EVERY legal risk — list each specific clause that could be "
            "unfavorable to the receiving party, non-standard, ambiguous, "
            "one-sided, potentially unenforceable, or that misaligns with the "
            "retrieved CONTEXT. Do not generalise multiple risks into one item; "
            "produce a SEPARATE risk entry for EACH problematic clause. Aim for "
            "completeness — if there are 8 risky clauses, the array must have 8 entries.\n"
            "\n"
            "5. Provide concrete recommendations — specific negotiation moves, "
            "clarifying language to request, or compliance steps.\n"
            "\n"
            "Ground every legal claim in CONTEXT.\n"
            "\n"
            f"DOCUMENT TEXT:\n{doc_text}\n\n"
            f"USER'S CONCERN (optional):\n{query or '(none provided)'}\n"
        )

    else:
        raise ValueError(f"Unhandled prompt mode: {mode}")

    # 4. Final reminder — strongest signal Gemini reliably respects.
    parts.append("Now produce the JSON object. Remember the RESPONSE LANGUAGE rule.")
    return "\n\n".join(parts)


def build_prompt(
    query: str,
    mode: PromptMode,
    chunks: list[RerankedChunk],
    language: str = "en",
    extras: dict | None = None,
    history: list[dict] | None = None,
) -> BuiltPrompt:
    """Assemble the system and user prompts for `mode`.

    `history` is an optional list of `{"role": "user"|"assistant", "content": str}`
    dicts representing prior turns of the same conversation. The most recent
    8 turns are included, each truncated to 1500 chars.
    """
    if language not in _LANGUAGE_INSTRUCTIONS:
        language = "en"
    schema = _SCHEMAS[mode]

    system = "\n\n".join(
        [
            _BASE_SYSTEM,
            _LANGUAGE_INSTRUCTIONS[language],
            (
                "Output a SINGLE valid JSON object — no markdown fences, no prose "
                "before or after — matching this schema (field types are described "
                "as strings):\n"
                f"{schema}"
            ),
            f"Always include this disclaimer text inside any 'warnings' array: \"{_DISCLAIMER}\"",
        ]
    )

    user = "\n\n".join(
        [
            _format_context_block(chunks),
            _user_block(query, mode, extras, history),
        ]
    )

    return BuiltPrompt(
        system=system,
        user=user,
        mode=mode,
        language=language,
        schema_hint=schema,
    )
