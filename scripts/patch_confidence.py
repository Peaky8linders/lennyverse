"""Patch `confidence`, `support_count`, `newest_source`, `oldest_source`
frontmatter in knowledge/wiki/concepts/*.md and knowledge/wiki/guests/*.md.

Uses source publish dates from knowledge/wiki/sources/*.md to score each
node via app.services.confidence_service. Lets us ship the v2 confidence
feature without re-running the full compile pipeline (which requires an LLM
for pass2 semantic extraction).

Same escape hatch pattern as scripts/patch_urls.py — runnable anytime
against an existing wiki without rebuilding from raw.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "backend"))

from app.services.confidence_service import score as score_confidence, score_tension  # noqa: E402
from app.services.frontmatter import inject_frontmatter, read_wiki_page  # noqa: E402

WIKI = REPO / "knowledge" / "wiki"


def load_source_dates() -> dict[str, str]:
    """Return {source_id: iso_date} for every compiled source page."""
    out: dict[str, str] = {}
    sources_dir = WIKI / "sources"
    if not sources_dir.exists():
        return out
    for md in sources_dir.glob("*.md"):
        meta, _ = read_wiki_page(md)
        out[md.stem] = str(meta.get("date", "") or "")
    return out


def patch_concepts(source_dates: dict[str, str]) -> int:
    concepts_dir = WIKI / "concepts"
    if not concepts_dir.exists():
        return 0
    n = 0
    for md in sorted(concepts_dir.glob("*.md")):
        meta, body = read_wiki_page(md)
        if not meta:
            continue
        appears_in = meta.get("appears_in", []) or []
        conf = score_confidence([source_dates.get(sid, "") for sid in appears_in])
        meta["confidence"] = conf.confidence
        meta["support_count"] = conf.support_count
        meta["newest_source"] = conf.newest_source
        meta["oldest_source"] = conf.oldest_source
        md.write_text(inject_frontmatter(meta, body), encoding="utf-8")
        n += 1
    return n


def patch_guests(source_dates: dict[str, str]) -> int:
    guests_dir = WIKI / "guests"
    if not guests_dir.exists():
        return 0
    n = 0
    for md in sorted(guests_dir.glob("*.md")):
        meta, body = read_wiki_page(md)
        if not meta:
            continue
        episodes = meta.get("episodes", []) or []
        conf = score_confidence([source_dates.get(sid, "") for sid in episodes])
        meta["confidence"] = conf.confidence
        meta["support_count"] = conf.support_count
        meta["newest_source"] = conf.newest_source
        meta["oldest_source"] = conf.oldest_source
        md.write_text(inject_frontmatter(meta, body), encoding="utf-8")
        n += 1
    return n


def patch_tensions(source_dates: dict[str, str]) -> int:
    """Patch tension pages with per-side confidence + supersession labels.

    No-op when the wiki has no tensions (which is the current state in
    environments where the LLM semantic pass hasn't run).
    """
    tensions_dir = WIKI / "tensions"
    if not tensions_dir.exists():
        return 0

    # Build concept_id -> appears_in map for scoring tension sides
    concept_appears: dict[str, list[str]] = {}
    concepts_dir = WIKI / "concepts"
    if concepts_dir.exists():
        for md in concepts_dir.glob("*.md"):
            meta, _ = read_wiki_page(md)
            concept_appears[md.stem] = meta.get("appears_in", []) or []

    n = 0
    for md in sorted(tensions_dir.glob("*.md")):
        meta, body = read_wiki_page(md)
        if not meta:
            continue
        concepts = meta.get("concepts", []) or []
        if len(concepts) < 2:
            continue
        a_id, b_id = concepts[0], concepts[1]
        a_dates = [source_dates.get(s, "") for s in concept_appears.get(a_id, [])]
        b_dates = [source_dates.get(s, "") for s in concept_appears.get(b_id, [])]
        a, b = score_tension(a_id, a_dates, b_id, b_dates)
        meta["side_a"] = {
            "label": a.label,
            "confidence": a.score.confidence,
            "support_count": a.score.support_count,
            "newest_source": a.score.newest_source,
            "oldest_source": a.score.oldest_source,
            "current": a.current,
        }
        meta["side_b"] = {
            "label": b.label,
            "confidence": b.score.confidence,
            "support_count": b.score.support_count,
            "newest_source": b.score.newest_source,
            "oldest_source": b.score.oldest_source,
            "current": b.current,
        }
        md.write_text(inject_frontmatter(meta, body), encoding="utf-8")
        n += 1
    return n


def main() -> None:
    source_dates = load_source_dates()
    print(f"Loaded {len(source_dates)} source dates")

    concepts = patch_concepts(source_dates)
    guests = patch_guests(source_dates)
    tensions = patch_tensions(source_dates)

    print(f"Concepts patched: {concepts}")
    print(f"Guests patched:   {guests}")
    print(f"Tensions patched: {tensions}")


if __name__ == "__main__":
    main()
