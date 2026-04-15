"""Confidence scoring for wiki nodes.

Implements LLM Wiki v2's confidence + supersession pattern, adapted for
LennyVerse's structure. Every scored node (concept, guest, tension side)
carries:

    confidence     float in [0, 1], rounded to 2 decimals
    support_count  int, number of distinct backing sources
    newest_source  ISO date string (YYYY-MM-DD) or ""
    oldest_source  ISO date string (YYYY-MM-DD) or ""

The scoring formula is intentionally small and auditable:

    confidence = 0.6 * normalized_support + 0.4 * recency_weight
    normalized_support = min(1.0, support_count / SUPPORT_SATURATION)
    recency_weight     = 0.5 ** (years_since_newest / RECENCY_HALF_LIFE)

Constants are tunable at the top of the file. Keep them module-level so the
formula is one `grep` away and unit tests can import them directly.

The service is pure: it takes lists of ISO date strings in, returns scores
out. No I/O, no frontmatter parsing, no LLM calls. Callers (compiler,
patch_confidence.py) are responsible for gathering source dates.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

# Tunable constants — also imported by tests.
SUPPORT_SATURATION = 5      # 5+ distinct sources = full support weight
RECENCY_HALF_LIFE = 2.0     # years; newer facts halve in weight every N years
SUPPORT_WEIGHT = 0.6        # weight on normalized_support in the final score
RECENCY_WEIGHT = 0.4        # weight on recency_weight in the final score

# Reference date for recency decay. Overridable in tests so fixtures can
# pin deterministic results across calendar time.
_reference_date: date | None = None


def set_reference_date(d: date | None) -> None:
    """Override 'now' for recency calculations. Tests only."""
    global _reference_date
    _reference_date = d


def _now() -> date:
    return _reference_date or datetime.utcnow().date()


def _parse(iso: str) -> date | None:
    if not iso:
        return None
    try:
        return date.fromisoformat(iso[:10])
    except ValueError:
        return None


@dataclass
class ConfidenceScore:
    confidence: float
    support_count: int
    newest_source: str
    oldest_source: str

    def as_frontmatter(self) -> dict:
        """Serialize to the frontmatter fields a caller should write."""
        return {
            "confidence": self.confidence,
            "support_count": self.support_count,
            "newest_source": self.newest_source,
            "oldest_source": self.oldest_source,
        }


def score(source_dates: list[str]) -> ConfidenceScore:
    """Compute a confidence score from a list of source publish dates.

    Args:
        source_dates: ISO date strings (YYYY-MM-DD) for each distinct source
            backing this claim. Empty/invalid dates are ignored for recency
            but still count toward support.

    Returns:
        ConfidenceScore with confidence, support_count, newest, oldest.
    """
    support_count = len(source_dates)
    if support_count == 0:
        return ConfidenceScore(confidence=0.0, support_count=0, newest_source="", oldest_source="")

    parsed = sorted([d for d in (_parse(s) for s in source_dates) if d is not None])
    newest = parsed[-1] if parsed else None
    oldest = parsed[0] if parsed else None

    normalized_support = min(1.0, support_count / SUPPORT_SATURATION)

    if newest is None:
        recency_weight = 0.0
    else:
        years_old = max(0.0, (_now() - newest).days / 365.25)
        recency_weight = 0.5 ** (years_old / RECENCY_HALF_LIFE)

    confidence = SUPPORT_WEIGHT * normalized_support + RECENCY_WEIGHT * recency_weight
    confidence = round(max(0.0, min(1.0, confidence)), 2)

    return ConfidenceScore(
        confidence=confidence,
        support_count=support_count,
        newest_source=newest.isoformat() if newest else "",
        oldest_source=oldest.isoformat() if oldest else "",
    )


@dataclass
class TensionSide:
    label: str                      # e.g. the concept id on this side
    score: ConfidenceScore
    current: bool                   # True iff this side has strictly higher confidence


def score_tension(
    side_a_label: str,
    side_a_dates: list[str],
    side_b_label: str,
    side_b_dates: list[str],
) -> tuple[TensionSide, TensionSide]:
    """Score both sides of a tension and mark the higher-confidence side `current`.

    Ties (equal confidence) produce two sides with `current=False` — the UI
    renders them as "contested, no consensus" rather than picking arbitrarily.
    """
    a = score(side_a_dates)
    b = score(side_b_dates)
    a_current = a.confidence > b.confidence
    b_current = b.confidence > a.confidence
    return (
        TensionSide(label=side_a_label, score=a, current=a_current),
        TensionSide(label=side_b_label, score=b, current=b_current),
    )
