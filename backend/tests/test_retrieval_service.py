"""Tests for retrieval_service.

Uses a tmp_path fixture that materializes a tiny fake wiki so we don't
depend on the real 129-node corpus. Covers tokenization, BM25 scoring,
seed extraction, graph walk, RRF, confidence reranking, and the
end-to-end retrieve() pipeline.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.services.retrieval_service import (
    RERANK_BASE,
    RERANK_SLOPE,
    RetrievalService,
    tokenize,
)


# ---------- Tiny fake wiki ----------

def _write(path: Path, meta_yaml: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{meta_yaml}---\n\n{body}\n", encoding="utf-8")


@pytest.fixture
def fake_wiki(tmp_path: Path) -> Path:
    wiki = tmp_path / "wiki"
    # Three concepts — each mentions distinct keywords and has different confidence
    _write(
        wiki / "concepts" / "product-management.md",
        "title: Product Management\ntype: concept\nconfidence: 0.9\nappears_in:\n- ep-paul\n",
        "Product management is the discipline of guiding a product's lifecycle. "
        "Involves roadmaps, user research, and prioritization frameworks like RICE.",
    )
    _write(
        wiki / "concepts" / "growth-loops.md",
        "title: Growth Loops\ntype: concept\nconfidence: 0.6\nappears_in:\n- ep-lenny\n",
        "Growth loops are self-reinforcing cycles where output of one cycle "
        "becomes input for the next. Often discussed in user acquisition contexts.",
    )
    _write(
        wiki / "concepts" / "pricing.md",
        "title: Pricing\ntype: concept\nconfidence: 0.4\nappears_in:\n- ep-lenny\n",
        "Pricing strategy matters enormously for SaaS products. Freemium vs "
        "trial vs reverse trial each have different conversion profiles.",
    )
    # One guest + two source episodes
    _write(
        wiki / "guests" / "lenny.md",
        "title: Lenny\ntype: guest\nconfidence: 1.0\nepisodes:\n- ep-lenny\n",
        "Lenny Rachitsky writes Lenny's Newsletter and hosts Lenny's Podcast about product.",
    )
    _write(
        wiki / "sources" / "ep-paul.md",
        "title: Paul on product management\ntype: source\nconfidence: 1.0\ndate: '2026-03-01'\n",
        "Paul Graham interview on product management fundamentals and founder mindset.",
    )
    _write(
        wiki / "sources" / "ep-lenny.md",
        "title: Lenny on growth loops and pricing\ntype: source\nconfidence: 1.0\ndate: '2026-04-01'\n",
        "Lenny discusses growth loops and pricing frameworks for early-stage startups.",
    )
    return wiki


@pytest.fixture
def service(fake_wiki: Path) -> RetrievalService:
    return RetrievalService(fake_wiki)


# ---------- Tokenization ----------

def test_tokenize_lowercases_and_strips_punctuation():
    assert tokenize("Growth LOOPS! (important)") == ["growth", "loops", "important"]


def test_tokenize_drops_stopwords_and_single_chars():
    # "a", "the", "is" are stopwords; "x" is single-char
    assert tokenize("a X is the only one") == ["only", "one"]


def test_tokenize_handles_empty_input():
    assert tokenize("") == []
    assert tokenize(None) == []  # type: ignore[arg-type]


# ---------- BM25 ----------

def test_bm25_returns_relevant_concept_first(service: RetrievalService):
    results = service.retrieve("product management roadmaps", top_k=5)
    assert results, "should return at least one result"
    assert results[0].node_id == "product-management"
    assert results[0].bm25_rank == 1


def test_bm25_finds_multiword_query(service: RetrievalService):
    results = service.retrieve("growth loops acquisition", top_k=5)
    assert any(r.node_id == "growth-loops" for r in results)


def test_bm25_ignores_unknown_terms(service: RetrievalService):
    # Query with zero overlap returns empty list (no walk seeds either)
    results = service.retrieve("quantum chromodynamics blockchain", top_k=5)
    assert results == []


# ---------- Seed extraction + graph walk ----------

def test_seed_extraction_matches_slug_as_phrase(service: RetrievalService):
    # Private method access is fine in tests
    service._ensure_index()
    assert "product-management" in service._extract_seeds("tell me about product management")


def test_seed_extraction_skips_sources(service: RetrievalService):
    # Source slugs shouldn't seed the graph walk
    service._ensure_index()
    seeds = service._extract_seeds("ep paul on stuff")
    assert not any(s.startswith("ep-") for s in seeds)


def test_graph_walk_surfaces_connected_nodes(service: RetrievalService):
    # 'product-management' connects to ep-paul via appears_in edge in fake wiki
    service._ensure_index()
    walk = dict(service._graph_walk(["product-management"], top_k=5))
    # The seed itself is always included as a walk hit
    assert "product-management" in walk


# ---------- RRF fusion ----------

def test_rrf_fuses_two_rankings():
    r1 = [("a", 1.0), ("b", 0.9), ("c", 0.8)]
    r2 = [("b", 0.7), ("a", 0.6), ("d", 0.5)]
    fused = RetrievalService._rrf_fuse(r1, r2)
    # 'a' and 'b' appear in both; 'a' rank 1+2, 'b' rank 2+1 — should tie
    assert fused["a"] == pytest.approx(fused["b"])
    # Both beat 'c' and 'd' which only appear once
    assert fused["a"] > fused["c"]
    assert fused["b"] > fused["d"]


# ---------- Confidence reranking ----------

def test_rerank_multiplier_matches_formula(service: RetrievalService):
    # Confidence 0.6 -> multiplier 0.5 + 0.5*0.6 = 0.8
    service._ensure_index()
    fused = {"growth-loops": 1.0}
    reranked = service._rerank_by_confidence(fused)
    assert reranked == [("growth-loops", pytest.approx(RERANK_BASE + RERANK_SLOPE * 0.6))]


def test_higher_confidence_wins_ties(service: RetrievalService):
    # Two concepts with the same fused score should sort by confidence
    service._ensure_index()
    fused = {"pricing": 1.0, "product-management": 1.0}
    reranked = service._rerank_by_confidence(fused)
    assert reranked[0][0] == "product-management"  # confidence 0.9 > 0.4


# ---------- End-to-end ----------

def test_retrieve_returns_results_with_confidence_and_ranks(service: RetrievalService):
    results = service.retrieve("product management", top_k=3)
    assert results
    top = results[0]
    # Phrase-matched concept wins over source via seed boost, even though
    # BM25 alone would rank the shorter source doc higher.
    assert top.node_id == "product-management"
    assert top.node_type == "concept"
    assert top.confidence == pytest.approx(0.9)
    assert top.bm25_rank is not None and top.bm25_rank >= 1
    assert top.graph_rank == 1  # seed always leads the walk ranking
    assert top.snippet  # non-empty
    assert top.score > 0


def test_retrieve_respects_top_k(service: RetrievalService):
    results = service.retrieve("product management growth loops pricing lenny", top_k=2)
    assert len(results) <= 2
