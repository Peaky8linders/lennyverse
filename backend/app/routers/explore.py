"""Explore API — Claude Q&A grounded in the compiled wiki."""
import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.config import config
from app.models import ExploreRequest
from app.rate_limit import limiter
from app.services.graph_service import GraphService
from app.services.llm_client import llm_stream

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["explore"])

EXPLORE_SYSTEM_PROMPT = """You are LennyVerse, a knowledge assistant for product management wisdom from Lenny's Newsletter and Podcast.

You answer questions using ONLY the provided wiki context below. You must:
1. Cite specific guests by name when referencing their ideas
2. Cite specific concepts and frameworks by their exact names
3. Note when guests disagree or have contrasting views
4. If the context doesn't contain enough info, say so honestly

When citing, use the format [concept-id] or [guest-id] so the frontend can link to graph nodes.

WIKI CONTEXT:
{context}
"""


def _build_context(question: str, context_node_id: str) -> str:
    """Build wiki context for the explore prompt."""
    svc = GraphService(config.wiki_path)

    index_path = config.wiki_path / "index.md"
    context_parts = []
    if index_path.exists():
        context_parts.append(f"## Wiki Index\n{index_path.read_text(encoding='utf-8')[:2000]}")

    if context_node_id:
        detail = svc.get_node_detail(context_node_id)
        if detail:
            context_parts.append(f"## Current Node: {detail.label}\n{detail.content}")
            for cn in detail.connected_nodes[:10]:
                neighbor = svc.get_node_detail(cn.id)
                if neighbor:
                    context_parts.append(f"## Connected: {neighbor.label}\n{neighbor.content[:500]}")

    if len(context_parts) < 3:
        graph = svc.build_graph()
        top_nodes = sorted(graph.nodes, key=lambda n: n.connections, reverse=True)[:10]
        for n in top_nodes:
            detail = svc.get_node_detail(n.id)
            if detail:
                context_parts.append(f"## {detail.label}\n{detail.content[:500]}")

    return "\n\n---\n\n".join(context_parts)


@router.post("/explore")
@limiter.limit("10/minute")
async def explore(request: Request, body: ExploreRequest):
    """Ask Claude a question grounded in the wiki. Returns SSE stream."""
    if not config.anthropic_api_key:
        async def err_stream():
            yield f"event: error\ndata: {json.dumps({'detail': 'Claude API not configured'})}\n\n"
        return StreamingResponse(err_stream(), media_type="text/event-stream")

    context = _build_context(body.question, body.context_node_id)
    system = EXPLORE_SYSTEM_PROMPT.format(context=context)

    async def event_stream():
        try:
            async for chunk in llm_stream(system=system, user_message=body.question):
                yield f"data: {json.dumps({'text': chunk})}\n\n"
            yield f"event: done\ndata: {json.dumps({'status': 'complete'})}\n\n"
        except Exception as e:
            logger.error("Explore stream error: %s", e)
            yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
