"""Explore API — Claude Q&A grounded in the compiled wiki."""
import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.config import config
from app.models import ExploreRequest
from app.rate_limit import limiter
from app.routers.graph import get_graph_service, get_retrieval_service
from app.services.llm_client import llm_stream
from app.services.retrieval_service import RetrievalResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["explore"])

EXPLORE_SYSTEM_PROMPT = """You are LennyVerse, a knowledge assistant for product management wisdom from Lenny's Newsletter and Podcast.

You answer questions using ONLY the provided wiki context below. You must:
1. Cite specific guests by name when referencing their ideas
2. Cite specific concepts and frameworks by their exact names
3. Note when guests disagree or have contrasting views
4. If the context doesn't contain enough info, say so honestly

When citing, use the format [concept-id] or [guest-id] so the frontend can link to graph nodes.
The context below is ranked by a hybrid BM25 + graph-walk retriever and includes a confidence
score for each source. Higher confidence means more backing episodes and more recent coverage —
prefer high-confidence sources when they conflict with low-confidence ones, and call out the
confidence gap when that's relevant.

WIKI CONTEXT:
{context}
"""


def _retrieve_context(question: str, context_node_id: str, top_k: int = 8) -> tuple[str, list[RetrievalResult]]:
    """Run hybrid retrieval and build a compact LLM context block.

    If a focal node is provided (user clicked it before asking), we prepend
    its full content so the model has the local frame. Then the top-k
    retrieved hits supply the global context, each with a one-line header
    naming the node id (for citations) and its confidence.

    Returns (context_string, hits) so the route can also emit hits as
    a sources event to the frontend.
    """
    graph_svc = get_graph_service()
    retrieval = get_retrieval_service()

    parts: list[str] = []

    if context_node_id:
        detail = graph_svc.get_node_detail(context_node_id)
        if detail:
            parts.append(f"## Focal node: [{detail.id}] {detail.label}\n{detail.content}")

    hits = retrieval.retrieve(question, top_k=top_k)
    for h in hits:
        # Use the full wiki body for concepts/guests, not just the snippet, so
        # Claude has enough to cite accurately. Sources get the snippet only —
        # their full body is usually a long transcript that would blow the budget.
        if h.node_type == "source":
            body = h.snippet
        else:
            detail = graph_svc.get_node_detail(h.node_id)
            body = (detail.content if detail else h.snippet) or h.snippet
        conf_pct = round(h.confidence * 100)
        parts.append(
            f"## [{h.node_id}] {h.title}  ({h.node_type}, confidence {conf_pct}%)\n{body[:800]}"
        )

    return "\n\n---\n\n".join(parts), hits


@router.post("/explore")
@limiter.limit("10/minute")
async def explore(request: Request, body: ExploreRequest):
    """Ask Claude a question grounded in the wiki. Returns SSE stream.

    Pipeline per request:
      1. Hybrid retrieval (BM25 + graph walk, RRF-fused, confidence-reranked)
      2. Emit a `sources` SSE event with the ranked hits so the UI can
         render citation cards immediately, before the LLM token stream
      3. Stream Claude's answer token-by-token as `data:` events
      4. Emit `done` when the stream finishes, or `error` on failure
    """
    if not config.anthropic_api_key:
        async def err_stream():
            yield f"event: error\ndata: {json.dumps({'detail': 'Claude API not configured'})}\n\n"
        return StreamingResponse(err_stream(), media_type="text/event-stream")

    context, hits = _retrieve_context(body.question, body.context_node_id)
    system = EXPLORE_SYSTEM_PROMPT.format(context=context)

    sources_payload = [
        {
            "node_id": h.node_id,
            "node_type": h.node_type,
            "title": h.title,
            "snippet": h.snippet,
            "confidence": h.confidence,
            "score": round(h.score, 4),
            "bm25_rank": h.bm25_rank,
            "graph_rank": h.graph_rank,
        }
        for h in hits
    ]

    async def event_stream():
        try:
            yield f"event: sources\ndata: {json.dumps({'sources': sources_payload})}\n\n"
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
