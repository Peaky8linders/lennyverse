"""Graph API routes — serve the compiled knowledge graph."""
from fastapi import APIRouter, HTTPException

from app.config import config
from app.models import GraphResponse, NodeDetail
from app.services.graph_service import GraphService

router = APIRouter(prefix="/api", tags=["graph"])

_graph_service: GraphService | None = None


def get_graph_service() -> GraphService:
    global _graph_service
    if _graph_service is None:
        _graph_service = GraphService(config.wiki_path)
    return _graph_service


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
