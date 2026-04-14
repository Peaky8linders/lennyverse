"""Parse and inject YAML frontmatter in wiki markdown files."""
from __future__ import annotations

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content.

    Returns (metadata_dict, body_text). If no frontmatter found,
    returns ({}, original_content).
    """
    if not content.startswith("---"):
        return {}, content

    end = content.find("---", 3)
    if end == -1:
        return {}, content

    yaml_block = content[3:end].strip()
    body = content[end + 3:].strip()

    try:
        meta = yaml.safe_load(yaml_block) or {}
    except yaml.YAMLError as e:
        logger.warning("Failed to parse frontmatter: %s", e)
        return {}, content

    return meta, body


def inject_frontmatter(meta: dict, body: str) -> str:
    """Create markdown content with YAML frontmatter."""
    yaml_str = yaml.dump(meta, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return f"---\n{yaml_str}---\n\n{body}\n"


def read_wiki_page(path: Path) -> tuple[dict, str]:
    """Read a wiki page file and return (frontmatter, body).

    Returns ({}, "") if file doesn't exist.
    """
    if not path.exists():
        return {}, ""
    content = path.read_text(encoding="utf-8")
    return parse_frontmatter(content)
