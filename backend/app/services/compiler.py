"""3-pass compilation pipeline: structure -> semantic -> Leiden clustering."""
from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from app.services.frontmatter import inject_frontmatter

logger = logging.getLogger(__name__)


class Compiler:
    """Compiles raw Lenny data into a wiki knowledge graph."""

    def __init__(self, raw_path: Path, wiki_path: Path):
        self.raw_path = raw_path
        self.wiki_path = wiki_path
        self.nodes: list[dict] = []
        self.edges: list[dict] = []
        self.guest_names: dict[str, str] = {}

    async def run_all(self):
        logger.info("=== PASS 1: Structure Extraction ===")
        self.pass1_structure()
        logger.info("Pass 1 complete: %d nodes, %d edges", len(self.nodes), len(self.edges))

        logger.info("=== PASS 2: Semantic Extraction ===")
        await self.pass2_semantic()
        logger.info("Pass 2 complete: %d nodes, %d edges", len(self.nodes), len(self.edges))

        logger.info("=== PASS 3: Community Detection ===")
        self.pass3_communities()
        logger.info("Pass 3 complete")

        logger.info("=== Writing wiki pages ===")
        self.write_wiki()
        logger.info("Compilation complete!")

    def pass1_structure(self):
        """Deterministic extraction from raw files and index.json."""
        index_path = self.raw_path / "index.json"
        if index_path.exists():
            try:
                index_data = json.loads(index_path.read_text(encoding="utf-8"))
                self._extract_from_index(index_data)
            except json.JSONDecodeError as e:
                logger.warning("Failed to parse index.json: %s", e)

        podcasts_dir = self.raw_path / "podcasts"
        if podcasts_dir.exists():
            for f in sorted(podcasts_dir.glob("*.md")):
                self._extract_structure_from_file(f, "podcast")

        newsletters_dir = self.raw_path / "newsletters"
        if newsletters_dir.exists():
            for f in sorted(newsletters_dir.glob("*.md")):
                self._extract_structure_from_file(f, "newsletter")

    def _extract_from_index(self, index_data):
        """Extract nodes from index.json metadata."""
        items = []
        source_type_by_idx: list[str] = []

        if isinstance(index_data, list):
            items = index_data
            source_type_by_idx = ["source"] * len(items)
        elif isinstance(index_data, dict):
            for key in ["podcasts", "newsletters", "items", "posts", "episodes", "transcripts"]:
                if key in index_data and isinstance(index_data[key], list):
                    for it in index_data[key]:
                        items.append(it)
                        if key == "podcasts":
                            source_type_by_idx.append("podcast")
                        elif key == "newsletters":
                            source_type_by_idx.append("newsletter")
                        else:
                            source_type_by_idx.append("source")

        for i, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            title = item.get("title", "")
            if not title:
                continue

            node_id = self._to_id(title)
            source_type = source_type_by_idx[i] if i < len(source_type_by_idx) else "source"

            if not any(n["id"] == node_id for n in self.nodes):
                self.nodes.append({
                    "id": node_id,
                    "type": "source",
                    "title": title,
                    "source_type": source_type,
                    "date": item.get("date", item.get("published_at", "")),
                    "word_count": item.get("word_count", 0),
                })

            guest = item.get("guest", item.get("guests", ""))
            if isinstance(guest, list):
                for g in guest:
                    self._add_guest(g, node_id)
            elif guest:
                self._add_guest(str(guest), node_id)

            # Extract concepts from description: "... covering X, Y, and Z."
            description = item.get("description", "") or item.get("subtitle", "")
            if description:
                self._extract_concepts_from_description(description, node_id, guest)

    def _extract_concepts_from_description(self, description: str, source_id: str, guest) -> None:
        """Extract concept nodes from `description` field by parsing 'covering A, B, and C'."""
        import re
        # Pattern: "covering X, Y, and Z" or "covering X and Y"
        match = re.search(r"covering\s+(.+?)(?:\.|$)", description, re.IGNORECASE)
        if not match:
            return
        topics_str = match.group(1)
        # Split on ", and", "and", ","
        topics_str = re.sub(r",\s*and\s+", ", ", topics_str)
        topics_str = re.sub(r"\s+and\s+", ", ", topics_str)
        topics = [t.strip().rstrip(".") for t in topics_str.split(",") if t.strip()]

        # Domain inference from topic keywords
        domain_keywords = {
            "Growth": ["growth", "acquisition", "retention", "funnel", "viral", "loops", "plg", "marketing"],
            "Product Strategy": ["product", "strategy", "roadmap", "prioritization", "vision", "discovery", "north star"],
            "Leadership": ["leadership", "team", "management", "culture", "hiring", "career"],
            "Career": ["career", "skill", "development", "interview", "resume", "promotion"],
            "Engineering": ["engineering", "code", "technical", "ai", "ml", "dev", "architecture"],
            "Design": ["design", "ux", "ui", "user", "research", "prototype"],
        }

        for topic in topics[:5]:
            if len(topic) < 3 or len(topic) > 60:
                continue
            concept_id = self._to_id(topic)
            # Infer domain
            lt = topic.lower()
            domain = "Uncategorized"
            best_score = 0
            for dname, kws in domain_keywords.items():
                score = sum(1 for kw in kws if kw in lt)
                if score > best_score:
                    best_score = score
                    domain = dname

            # Add or enrich concept node
            existing = next((n for n in self.nodes if n["id"] == concept_id and n["type"] == "concept"), None)
            if existing:
                if source_id not in existing.get("appears_in", []):
                    existing.setdefault("appears_in", []).append(source_id)
                if isinstance(guest, str) and guest:
                    gid = self._to_id(guest)
                    if gid not in existing.get("taught_by", []):
                        existing.setdefault("taught_by", []).append(gid)
            else:
                self.nodes.append({
                    "id": concept_id,
                    "type": "concept",
                    "title": topic.title() if topic.islower() else topic,
                    "domain": domain,
                    "summary": f"Topic from Lenny's Podcast: {topic}",
                    "confidence": 0.7,
                    "appears_in": [source_id],
                    "taught_by": [self._to_id(guest)] if isinstance(guest, str) and guest else [],
                })

            # Edges
            self.edges.append({
                "source": concept_id, "target": source_id, "type": "mentioned_in", "provenance": "EXTRACTED",
            })
            if isinstance(guest, str) and guest:
                gid = self._to_id(guest)
                self.edges.append({
                    "source": gid, "target": concept_id, "type": "teaches", "provenance": "EXTRACTED",
                })

    def _add_guest(self, name: str, source_id: str):
        name = name.strip()
        if not name:
            return
        gid = self._to_id(name)
        self.guest_names[gid] = name
        if not any(n["id"] == gid and n["type"] == "guest" for n in self.nodes):
            self.nodes.append({"id": gid, "type": "guest", "title": name, "domains": [], "episodes": []})
        for n in self.nodes:
            if n["id"] == gid and n["type"] == "guest":
                if source_id not in n.get("episodes", []):
                    n.setdefault("episodes", []).append(source_id)
                break
        self.edges.append({"source": gid, "target": source_id, "type": "appears_in", "provenance": "EXTRACTED"})

    def _extract_structure_from_file(self, path: Path, source_type: str):
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.warning("Failed to read %s: %s", path, e)
            return

        headers = re.findall(r"^#{1,3}\s+(.+)$", content, re.MULTILINE)

        file_id = self._to_id(path.stem)
        if not any(n["id"] == file_id for n in self.nodes):
            title = headers[0] if headers else path.stem.replace("-", " ").title()
            self.nodes.append({
                "id": file_id,
                "type": "source",
                "title": title,
                "source_type": source_type,
                "file": str(path.name),
            })

    async def pass2_semantic(self):
        """Use LLM (Claude or Ollama) to extract concepts, relationships, contradictions."""
        try:
            from app.services.llm_client import llm_generate, use_ollama  # noqa: F401
        except Exception:
            logger.warning("LLM client not available — skipping semantic extraction")
            return

        from app.config import config
        if not config.anthropic_api_key and not use_ollama():
            logger.warning("No LLM backend available — skipping semantic extraction")
            return

        if use_ollama():
            logger.info("Using Ollama model: %s", config.ollama_model)

        all_files = []
        for subdir in ["podcasts", "newsletters"]:
            d = self.raw_path / subdir
            if d.exists():
                all_files.extend(sorted(d.glob("*.md")))

        if not all_files:
            logger.warning("No raw files found for semantic extraction")
            return

        import asyncio
        # Ollama can only handle one request at a time; Claude handles parallel fine
        concurrency = 1 if use_ollama() else 5
        max_content = 6000 if use_ollama() else 15000
        semaphore = asyncio.Semaphore(concurrency)

        async def process_one(f: Path, idx: int, total: int):
            async with semaphore:
                try:
                    content = f.read_text(encoding="utf-8", errors="replace")
                    if len(content) > max_content:
                        content = content[:max_content] + "\n\n[... truncated]"
                    logger.info("[%d/%d] Extracting semantics from %s", idx + 1, total, f.name)
                    result = await self._extract_semantics(f.stem, content)
                    if result:
                        concept_count = len(result.get("concepts", []) or [])
                        logger.info("[%d/%d] %s → %d concepts", idx + 1, total, f.name, concept_count)
                    return f.stem, result
                except Exception as e:
                    logger.error("Semantic extraction failed for %s: %s", f.name, e)
                    return f.stem, None

        total = len(all_files)
        results = await asyncio.gather(*[process_one(f, i, total) for i, f in enumerate(all_files)])
        for source_id, result in results:
            if result:
                self._merge_semantic_result(result, self._to_id(source_id))

    async def _extract_semantics(self, source_id: str, content: str) -> dict | None:
        from app.services.llm_client import llm_generate

        system = """You are a knowledge extraction agent for a PM knowledge graph. Extract concepts, frameworks, and relationships from this content.

Respond in this EXACT JSON format with no markdown fences, no commentary, just JSON:
{
  "concepts": [
    {
      "id": "kebab-case-id",
      "title": "Human Readable Name",
      "summary": "1-2 sentence summary",
      "domain": "Growth",
      "confidence": 0.8
    }
  ],
  "relationships": [
    {
      "source": "concept-id-1",
      "target": "concept-id-2",
      "type": "builds_on",
      "confidence": 0.7
    }
  ],
  "guest_concepts": [
    {
      "guest_id": "guest-kebab-id",
      "concept_id": "concept-id",
      "relationship": "teaches"
    }
  ],
  "tensions": [
    {
      "concept_a": "concept-id-1",
      "concept_b": "concept-id-2",
      "description": "Brief description"
    }
  ]
}

Valid domains: Growth, Product Strategy, Leadership, Career, Engineering, Design
Valid relationship types: builds_on, contrasts_with, related
Valid guest relationships: teaches, advocates, critiques

Extract 3-8 key concepts. Focus on named frameworks, methodologies, and principles - not generic topics. Be specific."""

        raw = await llm_generate(system=system, user_message=content, max_tokens=2048)

        try:
            json_str = raw.strip()
            if "```" in json_str:
                parts = json_str.split("```")
                if len(parts) >= 2:
                    json_str = parts[1]
                    if json_str.startswith("json"):
                        json_str = json_str[4:]
            # Find first { to last }
            start = json_str.find("{")
            end = json_str.rfind("}")
            if start >= 0 and end >= 0:
                json_str = json_str[start:end+1]
            return json.loads(json_str.strip())
        except (json.JSONDecodeError, IndexError) as e:
            logger.warning("Failed to parse semantic extraction for %s: %s", source_id, e)
            return None

    def _merge_semantic_result(self, result: dict, source_id: str):
        for concept in result.get("concepts", []) or []:
            cid = concept.get("id")
            if not cid:
                continue
            existing = next((n for n in self.nodes if n["id"] == cid and n["type"] == "concept"), None)
            if existing:
                existing.setdefault("appears_in", [])
                if source_id not in existing["appears_in"]:
                    existing["appears_in"].append(source_id)
            else:
                self.nodes.append({
                    "id": cid,
                    "type": "concept",
                    "title": concept.get("title", cid),
                    "domain": concept.get("domain", "Uncategorized"),
                    "summary": concept.get("summary", ""),
                    "confidence": concept.get("confidence", 0.8),
                    "appears_in": [source_id],
                    "taught_by": [],
                })
            self.edges.append({
                "source": cid, "target": source_id, "type": "mentioned_in", "provenance": "EXTRACTED",
            })

        for rel in result.get("relationships", []) or []:
            self.edges.append({
                "source": rel.get("source", ""),
                "target": rel.get("target", ""),
                "type": rel.get("type", "related"),
                "provenance": "INFERRED",
                "confidence": rel.get("confidence", 0.7),
            })

        for gc in result.get("guest_concepts", []) or []:
            gid = gc.get("guest_id", "")
            cid = gc.get("concept_id", "")
            if not gid or not cid:
                continue
            self.edges.append({
                "source": gid, "target": cid, "type": "teaches", "provenance": "EXTRACTED",
            })
            for n in self.nodes:
                if n["id"] == cid and n["type"] == "concept":
                    n.setdefault("taught_by", [])
                    if gid not in n["taught_by"]:
                        n["taught_by"].append(gid)
                    break

        for tension in result.get("tensions", []) or []:
            ca = tension.get("concept_a", "")
            cb = tension.get("concept_b", "")
            if not ca or not cb:
                continue
            self.edges.append({
                "source": ca, "target": cb, "type": "contrasts_with",
                "provenance": "INFERRED", "label": tension.get("description", ""),
            })

    def pass3_communities(self):
        """Run Leiden community detection."""
        concept_nodes = [n for n in self.nodes if n["type"] == "concept"]
        if len(concept_nodes) < 3:
            logger.info("Too few concepts (%d) for community detection", len(concept_nodes))
            return

        try:
            import igraph as ig
            import leidenalg
        except ImportError:
            logger.warning("leidenalg/igraph not installed - skipping community detection")
            return

        id_to_idx = {n["id"]: i for i, n in enumerate(concept_nodes)}
        g = ig.Graph(n=len(concept_nodes))
        g.vs["name"] = [n["id"] for n in concept_nodes]

        edge_list = []
        for e in self.edges:
            src_idx = id_to_idx.get(e["source"])
            tgt_idx = id_to_idx.get(e["target"])
            if src_idx is not None and tgt_idx is not None and src_idx != tgt_idx:
                edge_list.append((src_idx, tgt_idx))

        if not edge_list:
            logger.info("No concept-to-concept edges for community detection")
            return

        g.add_edges(edge_list)
        partition = leidenalg.find_partition(g, leidenalg.ModularityVertexPartition)
        logger.info("Leiden found %d communities", len(partition))

        domain_labels = ["Growth", "Product Strategy", "Leadership", "Career", "Engineering", "Design"]
        used_labels = set()
        community_map: dict[int, str] = {}

        for comm_idx, members in enumerate(partition):
            domain_counts: dict[str, int] = defaultdict(int)
            for node_idx in members:
                node = concept_nodes[node_idx]
                d = node.get("domain", "")
                if d and d != "Uncategorized":
                    domain_counts[d] += 1

            if domain_counts:
                best = max(domain_counts, key=lambda k: domain_counts[k])
                community_map[comm_idx] = best
                used_labels.add(best)
            else:
                assigned = False
                for label in domain_labels:
                    if label not in used_labels:
                        community_map[comm_idx] = label
                        used_labels.add(label)
                        assigned = True
                        break
                if not assigned:
                    community_map[comm_idx] = f"Cluster {comm_idx + 1}"

        for comm_idx, members in enumerate(partition):
            domain = community_map[comm_idx]
            for node_idx in members:
                concept_nodes[node_idx]["domain"] = domain

    def write_wiki(self):
        """Write all nodes as wiki pages with frontmatter."""
        now = datetime.now(timezone.utc).isoformat()

        for subdir in ["concepts", "guests", "domains", "tensions"]:
            (self.wiki_path / subdir).mkdir(parents=True, exist_ok=True)

        edges_by_source: dict[str, list[dict]] = defaultdict(list)
        edges_by_target: dict[str, list[dict]] = defaultdict(list)
        for e in self.edges:
            edges_by_source[e["source"]].append(e)
            edges_by_target[e["target"]].append(e)

        # Concept pages
        for n in self.nodes:
            if n["type"] == "concept":
                related = list(set(
                    e["target"] for e in edges_by_source.get(n["id"], [])
                    if e["type"] in ("related", "builds_on") and e["target"] != n["id"]
                ))[:10]
                contrasts = list(set(
                    [e["target"] for e in edges_by_source.get(n["id"], []) if e["type"] == "contrasts_with"]
                    + [e["source"] for e in edges_by_target.get(n["id"], []) if e["type"] == "contrasts_with"]
                ))[:5]
                meta = {
                    "title": n["title"],
                    "domain": n.get("domain", "Uncategorized"),
                    "type": "concept",
                    "related": related,
                    "builds_on": [e["target"] for e in edges_by_source.get(n["id"], []) if e["type"] == "builds_on"][:5],
                    "contrasts_with": contrasts,
                    "appears_in": n.get("appears_in", [])[:10],
                    "taught_by": n.get("taught_by", [])[:5],
                    "confidence": n.get("confidence", 0.8),
                    "last_compiled": now,
                }
                body = n.get("summary", f"{n['title']} - extracted from Lenny's Newsletter and Podcast.")
                path = self.wiki_path / "concepts" / f"{n['id']}.md"
                path.write_text(inject_frontmatter(meta, body), encoding="utf-8")

        # Guest pages
        for n in self.nodes:
            if n["type"] == "guest":
                taught = list(set(
                    e["target"] for e in edges_by_source.get(n["id"], []) if e["type"] == "teaches"
                ))
                meta = {
                    "title": n["title"],
                    "type": "guest",
                    "domains": list(set(n.get("domains", []))),
                    "known_for": taught[:10],
                    "episodes": n.get("episodes", [])[:20],
                }
                body = f"{n['title']} - guest on Lenny's Podcast."
                path = self.wiki_path / "guests" / f"{n['id']}.md"
                path.write_text(inject_frontmatter(meta, body), encoding="utf-8")

        # Domain pages
        domain_concepts: dict[str, list[str]] = defaultdict(list)
        for n in self.nodes:
            if n["type"] == "concept":
                domain_concepts[n.get("domain", "Uncategorized")].append(n["id"])

        domain_colors = {
            "Growth": "#22c55e", "Product Strategy": "#3b82f6", "Leadership": "#a855f7",
            "Career": "#f59e0b", "Engineering": "#ef4444", "Design": "#ec4899", "Uncategorized": "#6b7280",
        }
        for domain_name, concept_ids in domain_concepts.items():
            did = self._to_id(domain_name)
            meta = {
                "title": domain_name,
                "type": "domain",
                "color": domain_colors.get(domain_name, "#6b7280"),
                "top_concepts": concept_ids[:10],
            }
            body = f"{domain_name} - {len(concept_ids)} concepts extracted from Lenny's content."
            path = self.wiki_path / "domains" / f"{did}.md"
            path.write_text(inject_frontmatter(meta, body), encoding="utf-8")

        # Tension pages
        tension_edges = [e for e in self.edges if e["type"] == "contrasts_with"]
        seen = set()
        for e in tension_edges:
            key = tuple(sorted([e["source"], e["target"]]))
            if key in seen:
                continue
            seen.add(key)
            tid = f"{key[0]}-vs-{key[1]}"[:80]
            meta = {
                "title": f"{key[0]} vs {key[1]}",
                "type": "tension",
                "concepts": list(key),
            }
            body = e.get("label") or f"Tension between {key[0]} and {key[1]}"
            path = self.wiki_path / "tensions" / f"{tid}.md"
            path.write_text(inject_frontmatter(meta, body), encoding="utf-8")

        self._write_index()
        self._write_log(now)
        self._write_report()

    def _write_index(self):
        lines = ["# LennyVerse Wiki Index\n"]
        by_domain: dict[str, list[dict]] = defaultdict(list)
        for n in self.nodes:
            if n["type"] == "concept":
                by_domain[n.get("domain", "Uncategorized")].append(n)

        for domain, concepts in sorted(by_domain.items()):
            lines.append(f"\n## {domain}\n")
            for c in sorted(concepts, key=lambda x: x["title"]):
                summary = (c.get("summary", "") or "")[:60]
                lines.append(f"- [{c['title']}](concepts/{c['id']}.md) - {summary}")

        guests = [n for n in self.nodes if n["type"] == "guest"]
        if guests:
            lines.append("\n## Guests\n")
            for g in sorted(guests, key=lambda x: x["title"]):
                lines.append(f"- [{g['title']}](guests/{g['id']}.md)")

        (self.wiki_path / "index.md").write_text("\n".join(lines), encoding="utf-8")

    def _write_log(self, timestamp: str):
        concept_count = len([n for n in self.nodes if n["type"] == "concept"])
        guest_count = len([n for n in self.nodes if n["type"] == "guest"])
        content = f"""# LennyVerse Ingestion Log

- {timestamp} - Full compilation: {concept_count} concepts, {guest_count} guests, {len(self.edges)} edges
"""
        (self.wiki_path / "log.md").write_text(content, encoding="utf-8")

    def _write_report(self):
        edge_counts: dict[str, int] = defaultdict(int)
        for e in self.edges:
            edge_counts[e["source"]] += 1
            edge_counts[e["target"]] += 1

        concept_nodes = [n for n in self.nodes if n["type"] == "concept"]
        top = sorted(concept_nodes, key=lambda n: edge_counts.get(n["id"], 0), reverse=True)[:5]

        lines = ["# LennyVerse Graph Report\n"]
        lines.append("## God Nodes (highest connectivity)\n")
        for n in top:
            lines.append(f"- **{n['title']}** - {edge_counts.get(n['id'], 0)} connections")

        lines.append("\n## Stats\n")
        lines.append(f"- Concepts: {len(concept_nodes)}")
        lines.append(f"- Guests: {len([n for n in self.nodes if n['type'] == 'guest'])}")
        lines.append(f"- Sources: {len([n for n in self.nodes if n['type'] == 'source'])}")
        lines.append(f"- Edges: {len(self.edges)}")
        lines.append(f"- Tensions: {len([e for e in self.edges if e['type'] == 'contrasts_with'])}")

        inferred = [e for e in self.edges if e.get("provenance") == "INFERRED"]
        lines.append(f"- Inferred connections: {len(inferred)}")

        report_path = self.wiki_path.parent / "GRAPH_REPORT.md"
        report_path.write_text("\n".join(lines), encoding="utf-8")

    @staticmethod
    def _to_id(text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^a-z0-9\s-]", "", text)
        text = re.sub(r"[\s]+", "-", text)
        text = re.sub(r"-+", "-", text)
        return text.strip("-")[:80]
