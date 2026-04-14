"""Tests for frontmatter parsing and injection."""
import tempfile
from pathlib import Path

from app.services.frontmatter import parse_frontmatter, inject_frontmatter, read_wiki_page


def test_parse_frontmatter_valid():
    content = """---
title: Product-Led Growth
domain: Growth
type: concept
related: [freemium, self-serve]
confidence: 0.87
---

PLG is a business methodology where product usage drives growth.
"""
    meta, body = parse_frontmatter(content)
    assert meta["title"] == "Product-Led Growth"
    assert meta["domain"] == "Growth"
    assert meta["related"] == ["freemium", "self-serve"]
    assert meta["confidence"] == 0.87
    assert "PLG is a business methodology" in body


def test_parse_frontmatter_no_frontmatter():
    content = "Just plain markdown without frontmatter."
    meta, body = parse_frontmatter(content)
    assert meta == {}
    assert body == content


def test_inject_frontmatter():
    meta = {
        "title": "North Star Metric",
        "domain": "Product Strategy",
        "type": "concept",
        "related": ["okrs", "kpis"],
        "confidence": 0.9,
    }
    body = "A North Star Metric is the single metric that best captures..."
    result = inject_frontmatter(meta, body)
    assert result.startswith("---\n")
    assert "title: North Star Metric" in result

    parsed_meta, parsed_body = parse_frontmatter(result)
    assert parsed_meta["title"] == "North Star Metric"
    assert parsed_meta["related"] == ["okrs", "kpis"]
    assert "A North Star Metric" in parsed_body


def test_read_wiki_page_file():
    content = """---
title: Test
type: concept
domain: Growth
---

Body text here.
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(content)
        temp_path = f.name
    try:
        meta, body = read_wiki_page(Path(temp_path))
        assert meta["title"] == "Test"
        assert "Body text here" in body
    finally:
        Path(temp_path).unlink()


def test_read_wiki_page_missing_file():
    meta, body = read_wiki_page(Path("/nonexistent/file.md"))
    assert meta == {}
    assert body == ""
