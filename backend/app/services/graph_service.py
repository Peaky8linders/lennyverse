"""Graph service — builds graph response from compiled wiki directory."""
from __future__ import annotations

import hashlib
import logging
import math
import random
from pathlib import Path

from app.models import (
    DomainSummary, GraphEdge, GraphNode, GraphReport, GraphResponse, NodeDetail,
)
from app.services.frontmatter import read_wiki_page

logger = logging.getLogger(__name__)

DEFAULT_DOMAIN_COLORS = {
    "Growth": "#22c55e",
    "Product Strategy": "#3b82f6",
    "Leadership": "#a855f7",
    "Career": "#f59e0b",
    "Engineering": "#ef4444",
    "Design": "#ec4899",
    "Uncategorized": "#6b7280",
}


class GraphService:
    """Reads wiki directory and builds a graph for the frontend."""

    def __init__(self, wiki_path: Path):
        self.wiki_path = wiki_path
        self._cache: GraphResponse | None = None
        self._cache_hash: str = ""

    def invalidate_cache(self):
        self._cache = None
        self._cache_hash = ""

    def build_graph(self) -> GraphResponse:
        """Build full graph from wiki pages. Cached until invalidated."""
        current_hash = self._compute_wiki_hash()
        if self._cache is not None and self._cache_hash == current_hash:
            return self._cache

        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        domain_map: dict[str, DomainSummary] = {}
        node_ids: set[str] = set()

        # 1. Read domain pages
        domains_dir = self.wiki_path / "domains"
        if domains_dir.exists():
            for f in sorted(domains_dir.glob("*.md")):
                meta, _body = read_wiki_page(f)
                if not meta.get("title"):
                    continue
                did = f.stem
                color = meta.get("color", DEFAULT_DOMAIN_COLORS.get(meta["title"], "#6b7280"))
                domain_map[meta["title"]] = DomainSummary(
                    id=did, label=meta["title"], color=color, node_count=0,
                )

        # 2. Read concept pages
        concepts_dir = self.wiki_path / "concepts"
        if concepts_dir.exists():
            for f in sorted(concepts_dir.glob("*.md")):
                meta, _body = read_wiki_page(f)
                if not meta.get("title"):
                    continue
                nid = f.stem
                domain = meta.get("domain", "Uncategorized")
                nodes.append(GraphNode(
                    id=nid, type="concept", label=meta["title"],
                    domain=domain,
                    confidence=float(meta.get("confidence", 1.0)),
                ))
                node_ids.add(nid)

                if domain in domain_map:
                    domain_map[domain].node_count += 1

                for target in meta.get("related", []) or []:
                    edges.append(GraphEdge(
                        id=f"{nid}--related--{target}", source=nid, target=target,
                        type="builds_on", provenance="INFERRED", label=f"related to {target}",
                    ))
                for target in meta.get("builds_on", []) or []:
                    edges.append(GraphEdge(
                        id=f"{nid}--builds_on--{target}", source=nid, target=target,
                        type="builds_on", provenance="EXTRACTED", label=f"builds on {target}",
                    ))
                for target in meta.get("contrasts_with", []) or []:
                    edges.append(GraphEdge(
                        id=f"{nid}--contrasts--{target}", source=nid, target=target,
                        type="contrasts_with", provenance="EXTRACTED", label=f"contrasts with {target}",
                    ))
                for guest_id in meta.get("taught_by", []) or []:
                    edges.append(GraphEdge(
                        id=f"{guest_id}--teaches--{nid}", source=guest_id, target=nid,
                        type="teaches", provenance="EXTRACTED", label=f"teaches {meta['title']}",
                    ))
                for source_id in meta.get("appears_in", []) or []:
                    edges.append(GraphEdge(
                        id=f"{nid}--mentioned_in--{source_id}", source=nid, target=source_id,
                        type="mentioned_in", provenance="EXTRACTED",
                    ))

        # 3. Read guest pages
        guests_dir = self.wiki_path / "guests"
        if guests_dir.exists():
            for f in sorted(guests_dir.glob("*.md")):
                meta, _body = read_wiki_page(f)
                if not meta.get("title"):
                    continue
                nid = f.stem
                domains = meta.get("domains", []) or []
                nodes.append(GraphNode(
                    id=nid, type="guest", label=meta["title"],
                    domain=domains[0] if domains else "",
                    known_for=meta.get("known_for", []) or [],
                ))
                node_ids.add(nid)

                for ep_id in meta.get("episodes", []) or []:
                    edges.append(GraphEdge(
                        id=f"{nid}--appears_in--{ep_id}", source=nid, target=ep_id,
                        type="appears_in", provenance="EXTRACTED",
                    ))

        # 4. Filter edges to only reference existing nodes
        edges = [e for e in edges if e.source in node_ids and e.target in node_ids]

        # 5. Compute connection counts
        connection_counts: dict[str, int] = {}
        for e in edges:
            connection_counts[e.source] = connection_counts.get(e.source, 0) + 1
            connection_counts[e.target] = connection_counts.get(e.target, 0) + 1
        for n in nodes:
            n.connections = connection_counts.get(n.id, 0)

        # 6. Ensure Uncategorized domain if needed
        if not domain_map:
            domain_map["Uncategorized"] = DomainSummary(
                id="uncategorized", label="Uncategorized", color="#6b7280", node_count=len(nodes),
            )

        # 7. Assign positions by domain
        self._assign_positions(nodes, domain_map)

        # 8. Build report
        god_nodes_sorted = sorted(nodes, key=lambda n: n.connections, reverse=True)[:5]
        report = GraphReport(
            god_nodes=[n.id for n in god_nodes_sorted],
            surprising_connections=len([e for e in edges if e.provenance == "INFERRED"]),
            last_compiled=self._get_last_compiled(),
        )

        graph = GraphResponse(
            nodes=nodes,
            edges=edges,
            domains=list(domain_map.values()),
            report=report,
        )
        self._cache = graph
        self._cache_hash = current_hash
        return graph

    def get_node_detail(self, node_id: str) -> NodeDetail | None:
        """Get detailed info for a single node."""
        for subdir in ["concepts", "guests", "domains", "tensions"]:
            path = self.wiki_path / subdir / f"{node_id}.md"
            if path.exists():
                meta, body = read_wiki_page(path)
                graph = self.build_graph()
                connections = [e for e in graph.edges if e.source == node_id or e.target == node_id]
                connected_ids = set()
                for e in connections:
                    connected_ids.add(e.source if e.source != node_id else e.target)
                connected_nodes = [n for n in graph.nodes if n.id in connected_ids]

                return NodeDetail(
                    id=node_id,
                    type=meta.get("type", "concept"),
                    label=meta.get("title", node_id),
                    domain=meta.get("domain", ""),
                    content=body,
                    frontmatter=meta,
                    connections=connections,
                    connected_nodes=connected_nodes,
                )
        return None

    def _assign_positions(self, nodes: list[GraphNode], domain_map: dict[str, DomainSummary]):
        """Assign x,y positions using circular layout per domain cluster."""
        by_domain: dict[str, list[GraphNode]] = {}
        for n in nodes:
            d = n.domain or "Uncategorized"
            by_domain.setdefault(d, []).append(n)

        domain_list = list(by_domain.keys())
        num_domains = max(len(domain_list), 1)
        domain_radius = 800

        rng = random.Random(42)

        for i, domain_name in enumerate(domain_list):
            angle = (2 * math.pi * i) / num_domains
            cx = domain_radius * math.cos(angle)
            cy = domain_radius * math.sin(angle)

            domain_nodes = by_domain[domain_name]
            node_radius = max(120, 40 * math.sqrt(len(domain_nodes)))

            for j, node in enumerate(domain_nodes):
                if len(domain_nodes) == 1:
                    node.position = {"x": cx, "y": cy}
                else:
                    a = (2 * math.pi * j) / len(domain_nodes)
                    jitter_x = rng.uniform(-30, 30)
                    jitter_y = rng.uniform(-30, 30)
                    node.position = {
                        "x": round(cx + node_radius * math.cos(a) + jitter_x, 1),
                        "y": round(cy + node_radius * math.sin(a) + jitter_y, 1),
                    }

            if domain_name in domain_map:
                for node in domain_nodes:
                    node.color = domain_map[domain_name].color

    def _compute_wiki_hash(self) -> str:
        parts = []
        if self.wiki_path.exists():
            for f in sorted(self.wiki_path.rglob("*.md")):
                parts.append(f"{f}:{f.stat().st_mtime}")
        return hashlib.md5("|".join(parts).encode()).hexdigest()

    def _get_last_compiled(self) -> str:
        log_path = self.wiki_path / "log.md"
        if log_path.exists():
            lines = log_path.read_text(encoding="utf-8").strip().split("\n")
            if lines:
                return lines[-1][:25] if lines[-1] else ""
        return ""
