"""Ingest API — add new content to the knowledge graph."""
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from app.config import config
from app.models import IngestRequest, IngestResponse
from app.rate_limit import limiter
from app.services.frontmatter import inject_frontmatter, read_wiki_page
from app.services.graph_service import GraphService
from app.services.llm_client import llm_generate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["ingest"])

INGEST_SYSTEM_PROMPT = """You are a knowledge compiler for LennyVerse, a PM knowledge graph.

Given new content, you must:
1. Decide if this is a NEW concept or ENRICHMENT of an existing concept
2. Extract the key concept/framework name
3. Determine which domain it belongs to (Growth, Product Strategy, Leadership, Career, Engineering, Design)
4. Identify related concepts, what it builds on, and what it contrasts with
5. Write a 2-3 sentence summary

Respond in this exact JSON format (no markdown, just JSON):
{{
  "action": "create",
  "concept_id": "kebab-case-id",
  "title": "Human Readable Title",
  "domain": "Domain Name",
  "summary": "2-3 sentence summary",
  "related": ["concept-id-1", "concept-id-2"],
  "builds_on": ["concept-id"],
  "contrasts_with": ["concept-id"],
  "confidence": 0.8
}}

EXISTING WIKI INDEX:
{index}
"""


@router.post("/ingest", response_model=IngestResponse)
@limiter.limit("5/minute")
async def ingest(request: Request, body: IngestRequest):
    """Ingest new content into the knowledge graph."""
    if not config.anthropic_api_key:
        raise HTTPException(status_code=503, detail="Claude API not configured")

    index_path = config.wiki_path / "index.md"
    index_content = ""
    if index_path.exists():
        index_content = index_path.read_text(encoding="utf-8")[:3000]

    system = INGEST_SYSTEM_PROMPT.format(index=index_content)
    user_msg = f"Title: {body.title}\nType: {body.type}\n\nContent:\n{body.content[:5000]}"

    raw_response = ""
    try:
        raw_response = await llm_generate(system=system, user_message=user_msg, max_tokens=1024)
        json_str = raw_response
        if "```" in json_str:
            json_str = json_str.split("```")[1]
            if json_str.startswith("json"):
                json_str = json_str[4:]
        result = json.loads(json_str.strip())
    except (json.JSONDecodeError, IndexError) as e:
        logger.error("Failed to parse ingest response: %s\nRaw: %s", e, raw_response[:500])
        raise HTTPException(status_code=500, detail="Failed to classify content")

    concept_id = result["concept_id"]
    wiki_path = config.wiki_path / "concepts" / f"{concept_id}.md"

    meta = {
        "title": result["title"],
        "domain": result["domain"],
        "type": body.type,
        "related": result.get("related", []),
        "builds_on": result.get("builds_on", []),
        "contrasts_with": result.get("contrasts_with", []),
        "confidence": result.get("confidence", 0.8),
        "last_compiled": datetime.now(timezone.utc).isoformat(),
    }

    action = "created"
    if wiki_path.exists():
        existing_meta, existing_body = read_wiki_page(wiki_path)
        meta = {**existing_meta, **{k: v for k, v in meta.items() if v}}
        for list_field in ["related", "builds_on", "contrasts_with"]:
            merged = list(set((existing_meta.get(list_field) or []) + (result.get(list_field) or [])))
            meta[list_field] = merged
        body_text = existing_body + f"\n\n## Update ({datetime.now(timezone.utc).strftime('%Y-%m-%d')})\n\n{result['summary']}"
        action = "enriched"
    else:
        body_text = result["summary"]

    wiki_path.parent.mkdir(parents=True, exist_ok=True)
    wiki_path.write_text(inject_frontmatter(meta, body_text), encoding="utf-8")

    inbox_path = config.raw_path / "inbox" / f"{concept_id}.md"
    inbox_path.parent.mkdir(parents=True, exist_ok=True)
    inbox_path.write_text(f"# {body.title}\n\n{body.content}", encoding="utf-8")

    _update_index(concept_id, result["title"], result["summary"][:80])
    _append_log(action, concept_id, result["title"])

    svc = GraphService(config.wiki_path)
    svc.invalidate_cache()

    return IngestResponse(
        node_id=concept_id,
        action=action,
        wiki_path=str(wiki_path.relative_to(config.wiki_path)),
    )


def _update_index(concept_id: str, title: str, summary: str):
    index_path = config.wiki_path / "index.md"
    entry = f"- [{title}](concepts/{concept_id}.md) - {summary}\n"
    if index_path.exists():
        content = index_path.read_text(encoding="utf-8")
        if concept_id not in content:
            content += entry
            index_path.write_text(content, encoding="utf-8")
    else:
        index_path.write_text(f"# LennyVerse Wiki Index\n\n## Concepts\n{entry}", encoding="utf-8")


def _append_log(action: str, concept_id: str, title: str):
    log_path = config.wiki_path / "log.md"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = f"- {timestamp} - {action} [{title}](concepts/{concept_id}.md)\n"
    if log_path.exists():
        content = log_path.read_text(encoding="utf-8")
        content += entry
    else:
        content = f"# LennyVerse Ingestion Log\n\n{entry}"
    log_path.write_text(content, encoding="utf-8")
