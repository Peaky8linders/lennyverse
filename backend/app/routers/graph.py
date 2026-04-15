"""Graph API routes — serve the compiled knowledge graph."""
from fastapi import APIRouter, HTTPException

from app.config import config
from app.models import (
    GraphResponse,
    NodeDetail,
    RetrievalHit,
    RetrieveRequest,
    RetrieveResponse,
)
from app.services.graph_service import GraphService
from app.services.retrieval_service import RetrievalService

router = APIRouter(prefix="/api", tags=["graph"])

_graph_service: GraphService | None = None
_retrieval_service: RetrievalService | None = None


def get_graph_service() -> GraphService:
    global _graph_service
    if _graph_service is None:
        _graph_service = GraphService(config.wiki_path)
    return _graph_service


def get_retrieval_service() -> RetrievalService:
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RetrievalService(config.wiki_path, get_graph_service())
    return _retrieval_service


@router.get("/graph", response_model=GraphResponse)
async def get_graph():
    """Return the full compiled knowledge graph."""
    svc = get_graph_service()
    return svc.build_graph()


@router.get("/node/{node_id}", response_model=NodeDetail)
async def get_node(node_id: str):
    """Return detailed info for a single node."""
    svc = get_graph_service()
    detail = svc.get_node_detail(node_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")
    return detail


@router.get("/report")
async def get_report():
    """Return the GRAPH_REPORT.md content."""
    report_path = config.wiki_path.parent / "GRAPH_REPORT.md"
    if not report_path.exists():
        return {"content": "No report generated yet. Run the compilation pipeline first."}
    return {"content": report_path.read_text(encoding="utf-8")}


@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve(body: RetrieveRequest):
    """Hybrid BM25 + graph-walk retrieval over the wiki.

    Returns confidence-reranked node hits with snippets. No LLM involved —
    this is the retrieval layer underneath /api/explore, exposed on its
    own for UI affordances and debugging.
    """
    svc = get_retrieval_service()
    hits = svc.retrieve(body.query, top_k=body.top_k)
    return RetrieveResponse(
        query=body.query,
        seeds=svc._extract_seeds(body.query),  # noqa: SLF001 — intentional debug surface
        results=[
            RetrievalHit(
                node_id=h.node_id,
                node_type=h.node_type,
                title=h.title,
                snippet=h.snippet,
                confidence=h.confidence,
                score=round(h.score, 4),
                bm25_rank=h.bm25_rank,
                graph_rank=h.graph_rank,
            )
            for h in hits
        ],
    )
