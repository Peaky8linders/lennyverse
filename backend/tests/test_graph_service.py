"""Tests for graph service — builds graph from wiki directory."""
import tempfile
from pathlib import Path

import pytest

from app.services.graph_service import GraphService


@pytest.fixture
def wiki_dir():
    """Create a temporary wiki directory with sample pages."""
    with tempfile.TemporaryDirectory() as tmpdir:
        wiki = Path(tmpdir)
        (wiki / "concepts").mkdir()
        (wiki / "guests").mkdir()
        (wiki / "domains").mkdir()
        (wiki / "tensions").mkdir()

        (wiki / "concepts" / "product-led-growth.md").write_text("""---
title: Product-Led Growth
domain: Growth
type: concept
related: [freemium, activation-metrics]
builds_on: [growth-loops]
contrasts_with: [sales-led-growth]
taught_by: [elena-verna]
appears_in: [ep-034]
confidence: 0.87
---

PLG is a go-to-market strategy that relies on the product itself as the primary driver of customer acquisition.
""", encoding="utf-8")

        (wiki / "guests" / "elena-verna.md").write_text("""---
title: Elena Verna
type: guest
domains: [Growth]
known_for: [PLG, Growth Loops]
episodes: [ep-034]
---

Elena Verna is a growth expert known for her work on product-led growth strategies.
""", encoding="utf-8")

        (wiki / "domains" / "growth.md").write_text("""---
title: Growth
type: domain
color: "#22c55e"
description: Strategies for growing products and user bases.
top_concepts: [product-led-growth, growth-loops, viral-coefficients]
---

Growth domain encompasses all strategies for acquiring and retaining users.
""", encoding="utf-8")

        yield wiki


def test_build_graph(wiki_dir):
    svc = GraphService(wiki_dir)
    graph = svc.build_graph()

    assert len(graph.nodes) >= 2
    concept = next((n for n in graph.nodes if n.id == "product-led-growth"), None)
    assert concept is not None
    assert concept.type == "concept"
    assert concept.label == "Product-Led Growth"
    assert concept.domain == "Growth"

    guest = next((n for n in graph.nodes if n.id == "elena-verna"), None)
    assert guest is not None
    assert guest.type == "guest"

    assert len(graph.edges) > 0
    teaches_edge = next((e for e in graph.edges if e.type == "teaches"), None)
    assert teaches_edge is not None
    assert teaches_edge.source == "elena-verna"
    assert teaches_edge.target == "product-led-growth"

    assert len(graph.domains) >= 1
    assert any(d.label == "Growth" for d in graph.domains)


def test_get_node_detail(wiki_dir):
    svc = GraphService(wiki_dir)
    detail = svc.get_node_detail("product-led-growth")
    assert detail is not None
    assert detail.label == "Product-Led Growth"
    assert "PLG is a go-to-market strategy" in detail.content
    assert len(detail.connections) > 0


def test_get_node_detail_missing(wiki_dir):
    svc = GraphService(wiki_dir)
    detail = svc.get_node_detail("nonexistent")
    assert detail is None


def test_graph_caching(wiki_dir):
    svc = GraphService(wiki_dir)
    g1 = svc.build_graph()
    g2 = svc.build_graph()
    assert g1 is g2
