"""Fast structural-only compile: runs pass 1 + pass 3, skips semantic LLM pass.

Same output as `compile.py` but without hitting Claude or Ollama. Useful when:
  - No ANTHROPIC_API_KEY set
  - No local Ollama available (or too slow)
  - You just want the graph to render from index.json metadata

Produces concepts derived from episode descriptions ("covering X, Y, Z"),
guest nodes, and episode (source) nodes, then runs Leiden clustering.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

from app.config import config  # noqa: E402
from app.services.compiler import Compiler  # noqa: E402


async def main() -> None:
    raw_path = config.raw_path
    wiki_path = config.wiki_path

    print(f"Raw data: {raw_path}")
    print(f"Wiki output: {wiki_path}")

    if not raw_path.exists():
        print(f"ERROR: Raw data directory not found: {raw_path}")
        sys.exit(1)

    podcast_count = len(list((raw_path / "podcasts").glob("*.md"))) if (raw_path / "podcasts").exists() else 0
    newsletter_count = len(list((raw_path / "newsletters").glob("*.md"))) if (raw_path / "newsletters").exists() else 0
    print(f"Found: {podcast_count} podcasts, {newsletter_count} newsletters")

    if podcast_count + newsletter_count == 0:
        print("ERROR: No raw files found.")
        sys.exit(1)

    compiler = Compiler(raw_path, wiki_path)

    print("=== PASS 1: Structure Extraction ===")
    compiler.pass1_structure()
    print(f"Pass 1: {len(compiler.nodes)} nodes, {len(compiler.edges)} edges")

    print("=== PASS 3: Community Detection ===")
    compiler.pass3_communities()

    print("=== Writing wiki pages ===")
    compiler.write_wiki()

    concept_count = len(list((wiki_path / "concepts").glob("*.md"))) if (wiki_path / "concepts").exists() else 0
    guest_count = len(list((wiki_path / "guests").glob("*.md"))) if (wiki_path / "guests").exists() else 0
    source_count = len(list((wiki_path / "sources").glob("*.md"))) if (wiki_path / "sources").exists() else 0
    print("\nCompilation complete!")
    print(f"  Concepts: {concept_count}")
    print(f"  Guests:   {guest_count}")
    print(f"  Sources:  {source_count}")
    print(f"  Wiki:     {wiki_path}")


if __name__ == "__main__":
    asyncio.run(main())
