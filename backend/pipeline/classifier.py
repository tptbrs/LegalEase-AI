"""Domain classifier for legal queries.

Maps a free-form user query to one of the project's legal domains. The classifier
is deliberately *rule-based with weighted lexicons* rather than ML:

  * No model load cost on every request (sub-millisecond classification).
  * Transparent — every score is explainable, which matters for the pipeline
    visualizer feature.
  * Bilingual: lexicons cover Indian English legal vocabulary plus common
    Hindi/Romanised-Hindi terms users actually type.

If no domain crosses the confidence floor, we return "general" — the retriever
then queries Chroma without a domain filter, which is the correct fallback.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Each entry is (keyword, weight). Weights let multi-word phrases dominate
# generic single tokens (e.g. "consumer protection" beats "consumer" alone).
_LEXICON: dict[str, list[tuple[str, float]]] = {
    "criminal": [
        ("fir", 3.0),
        ("first information report", 4.0),
        ("ipc", 3.0),
        ("bns", 3.0),
        ("bharatiya nyaya sanhita", 4.0),
        ("crpc", 3.0),
        ("bnss", 3.0),
        ("arrest", 2.0),
        ("bail", 2.0),
        ("murder", 2.0),
        ("theft", 2.0),
        ("assault", 2.0),
        ("rape", 2.5),
        ("dowry", 2.0),
        ("kidnapping", 2.0),
        ("police", 1.5),
        ("complaint", 1.0),
        ("chori", 2.0),
        ("hatya", 2.0),
        ("gaali", 1.5),
        ("dhamki", 2.0),
    ],
    "consumer": [
        ("consumer protection", 4.0),
        ("consumer forum", 3.5),
        ("consumer court", 3.5),
        ("defective product", 3.0),
        ("refund", 2.0),
        ("warranty", 2.0),
        ("e-commerce", 2.0),
        ("misleading advertisement", 3.0),
        ("deficiency in service", 3.5),
        ("upbhokta", 3.0),
        ("dhokha", 1.5),
    ],
    "labour": [
        ("industrial dispute", 3.5),
        ("provident fund", 3.0),
        ("epf", 2.5),
        ("gratuity", 2.5),
        ("minimum wage", 3.0),
        ("payment of wages", 3.0),
        ("employee", 1.5),
        ("employer", 1.5),
        ("retrenchment", 2.5),
        ("labour court", 3.0),
        ("trade union", 2.5),
        ("factories act", 3.0),
        ("workmen compensation", 3.0),
        ("vetan", 2.0),
        ("naukri", 1.5),
        ("majdoor", 2.0),
    ],
    "family": [
        ("divorce", 3.0),
        ("maintenance", 2.5),
        ("alimony", 2.5),
        ("custody", 2.5),
        ("hindu marriage", 3.0),
        ("muslim personal law", 3.0),
        ("special marriage act", 3.0),
        ("domestic violence", 3.0),
        ("dowry", 1.5),
        ("guardianship", 2.5),
        ("adoption", 2.0),
        ("talaq", 2.5),
        ("shaadi", 1.5),
        ("vivah", 2.0),
    ],
    "cyber": [
        ("cyber", 2.0),
        ("cybercrime", 3.5),
        ("hacking", 3.0),
        ("phishing", 3.0),
        ("data breach", 3.0),
        ("information technology act", 3.5),
        ("it act", 3.0),
        ("identity theft", 3.0),
        ("online fraud", 3.0),
        ("upi fraud", 3.0),
        ("otp", 1.5),
        ("digital arrest", 3.5),
        ("fake profile", 2.0),
    ],
    "property": [
        ("registration act", 2.5),
        ("transfer of property", 3.0),
        ("sale deed", 2.5),
        ("lease", 2.0),
        ("rent", 2.0),
        ("eviction", 2.5),
        ("landlord", 2.0),
        ("tenant", 2.0),
        ("encroachment", 2.5),
        ("title deed", 2.5),
        ("inheritance", 2.0),
        ("succession", 2.0),
        ("partition", 2.0),
        ("kabza", 2.5),
        ("makaan", 1.5),
        ("zameen", 2.0),
    ],
    "constitutional": [
        ("fundamental right", 3.5),
        ("article 14", 3.5),
        ("article 19", 3.5),
        ("article 21", 3.5),
        ("article 32", 3.5),
        ("writ", 2.5),
        ("habeas corpus", 3.0),
        ("public interest litigation", 3.5),
        ("pil", 2.0),
        ("supreme court", 1.5),
        ("constitutional", 2.0),
    ],
    "tax": [
        ("income tax", 3.0),
        ("gst", 3.0),
        ("tds", 2.5),
        ("itr", 2.5),
        ("assessment order", 2.5),
        ("notice under section 143", 3.0),
        ("tax evasion", 3.0),
        ("appellate tribunal", 2.0),
    ],
}

# Tokens that require word-boundary matching (avoid "ipc" matching "recipe").
_WORDY_TOKENS = re.compile(r"^[a-z]{2,}$")

_CONFIDENCE_FLOOR = 1.5  # below this, we return "general"


@dataclass(slots=True)
class ClassificationResult:
    domain: str
    confidence: float
    scores: dict[str, float]
    matched_keywords: list[str]


def _normalize(query: str) -> str:
    return query.lower().strip()


def _keyword_in(query: str, keyword: str) -> bool:
    if " " in keyword:
        return keyword in query
    if _WORDY_TOKENS.match(keyword):
        return re.search(rf"\b{re.escape(keyword)}\b", query) is not None
    return keyword in query


def classify(query: str) -> ClassificationResult:
    """Return the most likely legal domain for `query`.

    Scoring is the sum of weights of matched keywords per domain. The leading
    domain wins; if none crosses the confidence floor, the result is "general".
    """
    if not query or not query.strip():
        return ClassificationResult("general", 0.0, {}, [])

    norm = _normalize(query)
    scores: dict[str, float] = {}
    matched: list[str] = []

    for domain, entries in _LEXICON.items():
        score = 0.0
        for keyword, weight in entries:
            if _keyword_in(norm, keyword):
                score += weight
                matched.append(keyword)
        if score > 0:
            scores[domain] = round(score, 3)

    if not scores:
        return ClassificationResult("general", 0.0, {}, [])

    best_domain, best_score = max(scores.items(), key=lambda kv: kv[1])
    if best_score < _CONFIDENCE_FLOOR:
        return ClassificationResult("general", best_score, scores, matched)

    # Confidence = winning_score / sum_of_scores, clipped to [0,1].
    total = sum(scores.values())
    confidence = min(1.0, best_score / total) if total > 0 else 0.0

    return ClassificationResult(
        domain=best_domain,
        confidence=round(confidence, 3),
        scores=scores,
        matched_keywords=sorted(set(matched)),
    )
