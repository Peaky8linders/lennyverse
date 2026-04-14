"""Seed the raw/ directory with Lenny's free starter pack data.

Usage:
  1. Clone https://github.com/LennysNewsletter/lennys-newsletterpodcastdata
     or download from lennysdata.com
  2. Run: python scripts/seed_raw.py /path/to/lennys-data
"""
import shutil
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/seed_raw.py <path-to-lennys-data>")
        print("\nDownload from: https://github.com/LennysNewsletter/lennys-newsletterpodcastdata")
        sys.exit(1)

    source = Path(sys.argv[1])
    if not source.exists():
        print(f"ERROR: Source directory not found: {source}")
        sys.exit(1)

    raw_path = Path(__file__).parent.parent / "knowledge" / "raw"
    raw_path.mkdir(parents=True, exist_ok=True)

    podcast_dirs = [
        source / "podcasts",
        source / "transcripts",
        source / "podcast-transcripts",
        source,
    ]
    podcast_count = 0
    dest_podcasts = raw_path / "podcasts"
    dest_podcasts.mkdir(exist_ok=True)

    for pdir in podcast_dirs:
        if pdir.exists() and pdir.is_dir():
            for f in sorted(pdir.glob("*.md")):
                shutil.copy2(f, dest_podcasts / f.name)
                podcast_count += 1
            if podcast_count > 0:
                break

    newsletter_dirs = [
        source / "newsletters",
        source / "posts",
        source / "newsletter-posts",
    ]
    newsletter_count = 0
    dest_newsletters = raw_path / "newsletters"
    dest_newsletters.mkdir(exist_ok=True)

    for ndir in newsletter_dirs:
        if ndir.exists() and ndir.is_dir():
            for f in sorted(ndir.glob("*.md")):
                shutil.copy2(f, dest_newsletters / f.name)
                newsletter_count += 1
            if newsletter_count > 0:
                break

    for name in ["index.json", "metadata.json"]:
        idx = source / name
        if idx.exists():
            shutil.copy2(idx, raw_path / "index.json")
            print(f"Copied {name} -> index.json")
            break

    (raw_path / "inbox").mkdir(exist_ok=True)

    print("\nSeeded raw data:")
    print(f"  Podcasts:    {podcast_count} files -> {dest_podcasts}")
    print(f"  Newsletters: {newsletter_count} files -> {dest_newsletters}")
    print("\nReady to compile! Run: python scripts/compile.py")


if __name__ == "__main__":
    main()
