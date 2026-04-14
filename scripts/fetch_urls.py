"""Fetch Lenny's podcast catalog via Substack's per-post API and build a URL map.

Lenny's podcast URLs have hand-picked slugs that don't match episode titles
or guest names deterministically (e.g. Boris Cherny's episode is at
/p/head-of-claude-code-what-happens). The only reliable way to match our
starter-pack entries to real URLs is to fetch each post's metadata and
check its publish date + title.

Strategy:
  1. Fetch sitemap.xml for the full list of post slugs
  2. For each slug, fetch /api/v1/posts/{slug} to get (title, post_date, type)
  3. Cache the results locally (post_catalog.json)
  4. Match index.json entries by post_date (primary) + title/guest (tiebreaker)

The first run is slow (~300 HTTP requests, ~2 min). Subsequent runs use
the cache, so they finish in a second.

Produces: knowledge/url_map.json
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

SITEMAP_URL = "https://www.lennysnewsletter.com/sitemap.xml"
POST_API = "https://www.lennysnewsletter.com/api/v1/posts/"
POST_BASE = "https://www.lennysnewsletter.com/p/"
REPO_ROOT = Path(__file__).parent.parent
CATALOG_PATH = REPO_ROOT / "knowledge" / "post_catalog.json"


def _to_id(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def fetch_sitemap_slugs(max_slugs: int = 400) -> list[tuple[str, str]]:
    """Return (slug, lastmod) tuples from Lenny's sitemap, newest first."""
    print(f"Fetching {SITEMAP_URL}...")
    req = urllib.request.Request(
        SITEMAP_URL,
        headers={"User-Agent": "Mozilla/5.0 LennyVerse/1.0 (educational)"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        xml = resp.read().decode("utf-8")
    entries: list[tuple[str, str]] = []
    for match in re.finditer(
        r"<url><loc>https://www\.lennysnewsletter\.com/p/([^<]+)</loc>\s*(?:<lastmod>([^<]+)</lastmod>)?",
        xml,
    ):
        slug = match.group(1)
        lastmod = (match.group(2) or "")[:10]
        entries.append((slug, lastmod))
        if len(entries) >= max_slugs:
            break
    print(f"Got {len(entries)} slugs from sitemap")
    return entries


def load_catalog() -> dict[str, dict]:
    """Load the cached slug -> metadata catalog."""
    if CATALOG_PATH.exists():
        try:
            return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_catalog(catalog: dict[str, dict]) -> None:
    CATALOG_PATH.write_text(json.dumps(catalog, indent=2), encoding="utf-8")


def fetch_post_metadata(slug: str) -> dict | None:
    """Fetch one post's metadata via /api/v1/posts/{slug}."""
    url = POST_API + slug
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 LennyVerse/1.0 (educational)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return {
            "slug": slug,
            "title": data.get("title", "") or "",
            "post_date": (data.get("post_date") or "")[:10],
            "type": data.get("type", "") or "",
            "is_podcast": bool(data.get("podcast_duration")),
        }
    except Exception as e:
        return None


def build_catalog(slugs: list[tuple[str, str]], catalog: dict[str, dict]) -> dict[str, dict]:
    """Fetch metadata for slugs not yet in the catalog."""
    new_count = 0
    total = len(slugs)
    for i, (slug, _lastmod) in enumerate(slugs):
        if slug in catalog:
            continue
        meta = fetch_post_metadata(slug)
        if meta:
            catalog[slug] = meta
            new_count += 1
        if (i + 1) % 25 == 0:
            print(f"  Fetched metadata for {i + 1}/{total} posts ({new_count} new)")
            save_catalog(catalog)
        time.sleep(0.15)
    save_catalog(catalog)
    print(f"Catalog now has {len(catalog)} posts ({new_count} newly fetched)")
    return catalog


def _date_diff(a: str, b: str) -> int:
    try:
        return abs((date.fromisoformat(a[:10]) - date.fromisoformat(b[:10])).days)
    except Exception:
        return 9999


def match_entries(entries: list[dict], catalog: dict[str, dict]) -> tuple[dict[str, str], list[tuple[str, str]]]:
    """Match index.json entries to catalog posts by date + title/guest."""
    mapping: dict[str, str] = {}
    unmatched: list[tuple[str, str]] = []

    posts = list(catalog.values())

    for entry in entries:
        node_id = entry["node_id"]
        title = entry["title"]
        guest = entry.get("guest") or ""
        date_str = entry.get("date") or ""

        title_slug = _to_id(title)
        title_words = set(title_slug.split("-")) - {"the", "a", "an", "of", "to", "for"}
        guest_lower = guest.lower() if guest else ""

        best_slug = None
        best_score = 0.0

        for post in posts:
            pdate = post.get("post_date", "")
            ptitle = post.get("title", "")
            ptitle_slug = _to_id(ptitle)
            ptitle_lower = ptitle.lower()

            # Date match is the primary signal
            ddiff = _date_diff(date_str, pdate)
            if ddiff > 5:
                continue  # not the same episode

            date_score = 1.0 - (ddiff / 5.0)

            # Title similarity
            if guest_lower and guest_lower in ptitle_lower:
                # Guest name appears in post title — very strong signal
                title_score = 1.0
            else:
                post_words = set(ptitle_slug.split("-")) - {"the", "a", "an", "of", "to", "for"}
                if title_words and post_words:
                    overlap = len(title_words & post_words) / max(len(title_words | post_words), 1)
                    seq = SequenceMatcher(None, title_slug[:80], ptitle_slug[:80]).ratio()
                    title_score = (overlap * 0.5) + (seq * 0.5)
                else:
                    title_score = 0.0

            score = (date_score * 0.5) + (title_score * 0.5)

            if score > best_score:
                best_score = score
                best_slug = post["slug"]

        if best_slug and best_score > 0.55:
            mapping[node_id] = POST_BASE + best_slug
        else:
            query = guest if guest else title
            mapping[node_id] = (
                f"https://www.google.com/search?q=site%3Alennysnewsletter.com+{urllib.parse.quote(query)}"
            )
            unmatched.append((node_id, query))

    return mapping, unmatched


def main():
    index_path = REPO_ROOT / "knowledge" / "raw" / "index.json"
    if not index_path.exists():
        print(f"ERROR: {index_path} not found. Run scripts/seed_raw.py first.")
        sys.exit(1)

    with index_path.open(encoding="utf-8") as f:
        index = json.load(f)

    # Build entry list with dates for matching
    entries: list[dict] = []
    for item in index.get("podcasts", []):
        title = item.get("title", "")
        if title:
            guest = item.get("guest", "") or ""
            if isinstance(guest, list):
                guest = " ".join(guest)
            entries.append({
                "node_id": _to_id(title)[:80],
                "title": title,
                "guest": str(guest),
                "date": item.get("date", ""),
            })
    for item in index.get("newsletters", []):
        title = item.get("title", "")
        if title:
            entries.append({
                "node_id": _to_id(title)[:80],
                "title": title,
                "guest": "",
                "date": item.get("date", ""),
            })

    print(f"Loaded {len(entries)} entries from index.json")

    # Determine date range of our starter pack so we know how much of the
    # sitemap to crawl. Newest ~400 posts should cover ~6 months.
    dates = sorted([e["date"] for e in entries if e["date"]], reverse=True)
    print(f"Entry date range: {dates[-1] if dates else '?'} to {dates[0] if dates else '?'}")

    # Fetch sitemap slugs (newest first, cap at 400)
    slugs = fetch_sitemap_slugs(max_slugs=400)

    # Build/refresh catalog — cached in knowledge/post_catalog.json
    catalog = load_catalog()
    print(f"Loaded cached catalog with {len(catalog)} entries")
    catalog = build_catalog(slugs, catalog)

    # Match
    mapping, unmatched = match_entries(entries, catalog)
    real_count = len(mapping) - len(unmatched)
    print(f"\nReal Lenny URLs matched: {real_count} / {len(entries)}")
    print(f"Google search fallbacks:  {len(unmatched)} / {len(entries)}")
    if unmatched:
        print("\nFell back to Google site-search for:")
        for node_id, q in unmatched[:15]:
            try:
                print(f"  - {q}")
            except UnicodeEncodeError:
                safe = q.encode("ascii", "replace").decode("ascii")
                print(f"  - {safe}")

    out_path = REPO_ROOT / "knowledge" / "url_map.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2)
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
