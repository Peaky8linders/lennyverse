"""LennyVerse — Pydantic v2 request/response models."""
from __future__ import annotations

from pydantic import BaseModel, Field


# --- Graph response models ---

class GraphNode(BaseModel):
    id: str
    type: str  # concept | guest | source | domain
    label: str
    domain: str = ""
    confidence: float = 1.0
    support_count: int = 0
    newest_source: str = ""
    oldest_source: str = ""
    connections: int = 0
    position: dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})
    source_type: str = ""
    date: str = ""
    known_for: list[str] = Field(default_factory=list)
    color: str = ""
    url: str = ""  # external link (e.g., Lenny's Substack URL for sources)
    description: str = ""


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str  # teaches | appears_in | belongs_to | builds_on | contrasts_with | debates | mentioned_in
    provenance: str = "EXTRACTED"  # EXTRACTED | INFERRED | AMBIGUOUS
    confidence: float = 1.0
    label: str = ""


class GraphReport(BaseModel):
    god_nodes: list[str] = Field(default_factory=list)
    surprising_connections: int = 0
    last_compiled: str = ""
    suggested_questions: list[str] = Field(default_factory=list)


class DomainSummary(BaseModel):
    id: str
    label: str
    color: str
    node_count: int = 0


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    domains: list[DomainSummary]
    report: GraphReport


# --- Node detail ---

class NodeDetail(BaseModel):
    id: str
    type: str
    label: str
    domain: str = ""
    content: str = ""
    frontmatter: dict = Field(default_factory=dict)
    connections: list[GraphEdge] = Field(default_factory=list)
    connected_nodes: list[GraphNode] = Field(default_factory=list)


# --- Explore (Ask Claude) ---

class ExploreRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)
    context_node_id: str = ""


class ExploreChunk(BaseModel):
    text: str
    citations: list[str] = Field(default_factory=list)


# --- Ingest ---

class IngestRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=10)
    source: str = "manual"
    type: str = "concept"


class IngestResponse(BaseModel):
    node_id: str
    action: str
    wiki_path: str


# --- Error ---

class ErrorResponse(BaseModel):
    error: str
    detail: str = ""
