"""Fetch guest + episode cover art from Lenny's podcast RSS feed.

Why: Lenny's podcast RSS (Substack-hosted) exposes a unique <itunes:image> per
episode. Each cover contains the guest's headshot. This script mirrors the
approach Ben Shih used for LennyRPG (see "How I built LennyRPG" post) but
stops at extracting URLs — no avatar generation, just the CDN URLs — so the
frontend can hotlink them directly.

Inputs:
  - https://api.substack.com/feed/podcast/10845.rss   (Lenny's Podcast RSS, public)
  - https://github.com/LennysNewsletter/lennys-newsletterpodcastdata/.../index.json
    (free starter-pack metadata with `guest` field per episode)

Outputs (written into frontend/public/ so Vite serves them as static JSON):
  - guest_images.json    { "<guest-slug>": "<image_url>" }
  - episode_images.json  { "ep-<title-slug>": "<image_url>" }

The guest slug matches the backend's `Compiler._to_id(name)` so frontend can
look up images by the same IDs the `/api/graph` endpoint returns.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

RSS_URL = "https://api.substack.com/feed/podcast/10845.rss"
INDEX_URL = (
    "https://raw.githubusercontent.com/LennysNewsletter/"
    "lennys-newsletterpodcastdata/main/index.json"
)

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "frontend" / "public"


def to_id(text: str) -> str:
    """Match backend/app/services/compiler.py::Compiler._to_id exactly."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")[:80]


def normalize_title(title: str) -> str:
    """Loose match key: lowercase, alnum+space only, collapsed whitespace."""
    t = re.sub(r"[^a-z0-9\s]", " ", title.lower())
    return re.sub(r"\s+", " ", t).strip()


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "lennyverse-scraper/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def parse_rss(xml: str) -> list[dict]:
    """Return a list of {title, image, pub_date} for every <item> in the feed."""
    items = []
    for raw in re.findall(r"<item>(.*?)</item>", xml, re.DOTALL):
        tm = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>", raw, re.DOTALL) or \
             re.search(r"<title>([^<]+)</title>", raw)
        im = re.search(r'<itunes:image href="([^"]+)"', raw)
        pm = re.search(r"<pubDate>([^<]+)</pubDate>", raw)
        if not (tm and im):
            continue
        items.append({
            "title": tm.group(1).strip(),
            "image": im.group(1).strip(),
            "pub_date": pm.group(1).strip() if pm else "",
        })
    return items


def extract_guest_from_title(title: str) -> str | None:
    """Lenny's titles often follow `<topic> | <Guest Name> (<affiliation>)`.

    Returns the guest name if a `| Name` pattern is found, else None.
    """
    if "|" not in title:
        return None
    guest_part = title.split("|", 1)[1].strip()
    # Strip trailing "(affiliation)" or ", affiliation"
    guest_part = re.sub(r"\s*\(.*?\)\s*$", "", guest_part)
    guest_part = re.sub(r",.*$", "", guest_part)
    # Reject if it looks like a phrase (too many lowercase words)
    words = guest_part.split()
    if not words or len(words) > 6:
        return None
    cap_ratio = sum(1 for w in words if w and w[0].isupper()) / len(words)
    if cap_ratio < 0.6:
        return None
    return guest_part.strip()


def main() -> int:
    print(f"Fetching RSS feed: {RSS_URL}")
    rss_xml = fetch(RSS_URL).decode("utf-8", errors="replace")
    rss_items = parse_rss(rss_xml)
    print(f"  parsed {len(rss_items)} episodes")

    print(f"Fetching index.json: {INDEX_URL}")
    index_bytes = fetch(INDEX_URL)
    index_data = json.loads(index_bytes)
    if isinstance(index_data, dict):
        index_items = index_data.get("podcasts", [])
    else:
        index_items = index_data
    print(f"  loaded {len(index_items)} index entries")

    # Title -> RSS item (for matching index.json entries)
    rss_by_norm = {normalize_title(it["title"]): it for it in rss_items}

    # 1. Episode images — keyed by backend "ep-<slug>" for ALL RSS entries
    episode_images: dict[str, str] = {}
    for it in rss_items:
        eid = f"ep-{to_id(it['title'])}"
        episode_images[eid] = it["image"]
    print(f"  episode_images: {len(episode_images)}")

    # 2. Guest images — seed from index.json (authoritative `guest` field),
    #    then fall back to title extraction for RSS entries the index didn't cover.
    guest_latest: dict[str, tuple[str, str]] = {}  # guest_slug -> (pub_date, image)

    def record(name: str, pub_date: str, image: str) -> None:
        if not name:
            return
        slug = to_id(name)
        prev = guest_latest.get(slug)
        if prev is None or pub_date > prev[0]:
            guest_latest[slug] = (pub_date, image)

    matched_from_index = 0
    for entry in index_items:
        if not isinstance(entry, dict):
            continue
        title = entry.get("title") or ""
        guest = entry.get("guest") or entry.get("guests") or ""
        if not title or not guest:
            continue
        rss_hit = rss_by_norm.get(normalize_title(title))
        if not rss_hit:
            continue
        matched_from_index += 1
        if isinstance(guest, list):
            for g in guest:
                record(str(g), rss_hit["pub_date"], rss_hit["image"])
        else:
            record(str(guest), rss_hit["pub_date"], rss_hit["image"])

    matched_from_title = 0
    for it in rss_items:
        guest = extract_guest_from_title(it["title"])
        if not guest:
            continue
        slug = to_id(guest)
        if slug in guest_latest:
            # If index already supplied this guest, keep whichever is more recent
            prev_date = guest_latest[slug][0]
            if it["pub_date"] <= prev_date:
                continue
        record(guest, it["pub_date"], it["image"])
        matched_from_title += 1

    guest_images = {slug: img for slug, (_date, img) in guest_latest.items()}
    print(f"  guest_images: {len(guest_images)} "
          f"(index-matched={matched_from_index}, title-extracted={matched_from_title})")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "guest_images.json").write_text(
        json.dumps(guest_images, indent=2, sort_keys=True), encoding="utf-8"
    )
    (OUT_DIR / "episode_images.json").write_text(
        json.dumps(episode_images, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(f"Wrote {OUT_DIR / 'guest_images.json'}")
    print(f"Wrote {OUT_DIR / 'episode_images.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
