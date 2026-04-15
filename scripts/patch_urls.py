"""Patch `url:` frontmatter in knowledge/wiki/sources/*.md from url_map.json.

Avoids the full compile pipeline (which hangs without Ollama/Anthropic).
"""
import json
import re
from pathlib import Path

REPO = Path(__file__).parent.parent
WIKI_SOURCES = REPO / "knowledge" / "wiki" / "sources"
URL_MAP = REPO / "knowledge" / "url_map.json"

url_map = json.loads(URL_MAP.read_text(encoding="utf-8"))

patched = 0
skipped = 0
missing = 0
for md in sorted(WIKI_SOURCES.glob("*.md")):
    # wiki file id is `ep-<slug>`; url_map keys are `<slug>`
    slug = md.stem[3:] if md.stem.startswith("ep-") else md.stem
    new_url = url_map.get(slug)
    if not new_url:
        missing += 1
        continue
    text = md.read_text(encoding="utf-8")
    new_text, n = re.subn(r"^url:.*$", f"url: {new_url}", text, count=1, flags=re.MULTILINE)
    if n == 0:
        skipped += 1
        continue
    if new_text == text:
        skipped += 1
        continue
    md.write_text(new_text, encoding="utf-8")
    patched += 1

print(f"Patched: {patched}")
print(f"Unchanged: {skipped}")
print(f"Not in url_map: {missing}")
