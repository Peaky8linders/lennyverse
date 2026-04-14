"""CLI entry point: run the 3-pass compilation pipeline."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.config import config  # noqa: E402
from app.services.compiler import Compiler  # noqa: E402


async def main():
    raw_path = config.raw_path
    wiki_path = config.wiki_path

    print(f"Raw data: {raw_path}")
    print(f"Wiki output: {wiki_path}")

    if not raw_path.exists():
        print(f"ERROR: Raw data directory not found: {raw_path}")
        print("Run seed_raw.py first to populate the raw data.")
        sys.exit(1)

    podcast_count = len(list((raw_path / "podcasts").glob("*.md"))) if (raw_path / "podcasts").exists() else 0
    newsletter_count = len(list((raw_path / "newsletters").glob("*.md"))) if (raw_path / "newsletters").exists() else 0
    print(f"Found: {podcast_count} podcasts, {newsletter_count} newsletters")

    if podcast_count + newsletter_count == 0:
        print("ERROR: No raw files found. Populate knowledge/raw/ first.")
        sys.exit(1)

    compiler = Compiler(raw_path, wiki_path)
    await compiler.run_all()

    concept_count = len(list((wiki_path / "concepts").glob("*.md")))
    guest_count = len(list((wiki_path / "guests").glob("*.md")))
    print("\nCompilation complete!")
    print(f"  Concepts: {concept_count}")
    print(f"  Guests: {guest_count}")
    print(f"  Wiki: {wiki_path}")


if __name__ == "__main__":
    asyncio.run(main())
