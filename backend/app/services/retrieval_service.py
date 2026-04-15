"""Hybrid retrieval over the LennyVerse wiki.

Implements the second half of the LLM Wiki v2 pattern: BM25 lexical search
over wiki bodies, plus an entity-seeded graph walk, plus reciprocal rank
fusion, plus confidence-weighted re-ranking. Returns ranked nodes suitable
for feeding to Claude as citation-grounded context (or for rendering
standalone in the UI via /api/retrieve).

Design decisions:

- **BM25 only, no vector embeddings.** A 129-node corpus doesn't justify
  the weight of sentence-transformers (~500MB model) or the cost of an
  embeddings API (Voyage/OpenAI). BM25 captures enough signal and stays
  deterministic, dependency-free, and key-free. Vector search is a
  future upgrade path — see `_fuse()` for where a third ranking slots in.

- **Entity seeds via substring match.** The graph walk needs starting
  nodes. We tokenize the query, lowercase-match tokens against node ids
  (which are slug-form of titles), and take up to 3 seeds. Cheap and
  deterministic; good enough for PM vocabulary.

- **RRF with k=60.** Standard choice from the original RRF paper
  (Cormack et al.). Combines the BM25 ranking and the graph-walk
  ranking without needing score calibration.

- **Confidence as a re-ranking multiplier.** `(0.5 + 0.5 * confidence)`
  keeps zero-confidence nodes visible (halved) while boosting
  high-confidence ones. Direct payoff from the v2 confidence pipeline.

The service is pure-ish: it reads the wiki once via `GraphService.build_graph()`
plus `get_node_detail()` for bodies, caches the BM25 parameters, and exposes
`retrieve(query, top_k)` as the only public entry point.
"""
from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.services.frontmatter import read_wiki_page
from app.services.graph_service import GraphService

logger = logging.getLogger(__name__)

# BM25 constants — standard Lucene defaults.
BM25_K1 = 1.5
BM25_B = 0.75

# RRF fusion constant — the k in 1/(k+rank).
RRF_K = 60

# Confidence re-rank: score *= BASE + SLOPE * confidence
RERANK_BASE = 0.5
RERANK_SLOPE = 0.5

# English stopwords — small, domain-appropriate. Kept inline so the
# retrieval service has zero non-stdlib deps beyond what the project
# already uses (pyyaml, pydantic).
_STOPWORDS = frozenset(
    """
    a about an and are as at be but by for from has have he her his i in is it its me my of on or
    our she that the their them they this to us was we were what when where which who why will
    with you your
    """.split()
)

_WORD_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercase, strip punctuation, drop stopwords and single chars."""
    if not text:
        return []
    tokens = _WORD_RE.findall(text.lower())
    return [t for t in tokens if len(t) > 1 and t not in _STOPWORDS]


@dataclass
class Doc:
    """One indexed wiki document."""

    node_id: str
    node_type: str          # concept | guest | source
    title: str
    body: str
    snippet: str            # first ~240 chars of body for UI
    confidence: float
    tokens: list[str] = field(default_factory=list)
    tf: dict[str, int] = field(default_factory=dict)
    length: int = 0


@dataclass
class RetrievalResult:
    """One ranked hit returned by retrieve()."""

    node_id: str
    node_type: str
    title: str
    snippet: str
    confidence: float
    score: float            # final fused + reranked score
    bm25_rank: int | None   # 1-indexed rank in BM25 ranking, None if absent
    graph_rank: int | None  # 1-indexed rank in graph-walk ranking


class RetrievalService:
    """BM25 + graph walk + RRF over the wiki, cached by wiki mtime hash."""

    def __init__(self, wiki_path: Path, graph_service: GraphService | None = None):
        self.wiki_path = wiki_path
        self.graph_service = graph_service or GraphService(wiki_path)
        self._docs: list[Doc] = []
        self._doc_by_id: dict[str, Doc] = {}
        self._idf: dict[str, float] = {}
        self._avgdl: float = 0.0
        self._edges_by_node: dict[str, set[str]] = {}
        self._cache_hash: str = ""

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def _ensure_index(self) -> None:
        """Rebuild the BM25 index + edge adjacency if the wiki has changed."""
        current_hash = self._wiki_hash()
        if current_hash == self._cache_hash and self._docs:
            return
        logger.info("Rebuilding retrieval index (wiki changed)")
        self._build_index()
        self._cache_hash = current_hash

    def _wiki_hash(self) -> str:
        # Same hashing strategy as GraphService: file paths + mtimes.
        import hashlib
        parts = []
        for subdir in ("concepts", "guests", "sources"):
            d = self.wiki_path / subdir
            if d.exists():
                for f in sorted(d.glob("*.md")):
                    parts.append(f"{f}:{f.stat().st_mtime}")
        return hashlib.md5("|".join(parts).encode()).hexdigest()

    def _build_index(self) -> None:
        self._docs = []
        self._doc_by_id = {}

        # 1. Load every indexable wiki page into a Doc
        for subdir, node_type in (("concepts", "concept"), ("guests", "guest"), ("sources", "source")):
            d = self.wiki_path / subdir
            if not d.exists():
                continue
            for f in sorted(d.glob("*.md")):
                meta, body = read_wiki_page(f)
                title = str(meta.get("title") or f.stem)
                confidence = float(meta.get("confidence", 1.0) or 1.0)
                text = f"{title}\n{body}"
                tokens = tokenize(text)
                tf: dict[str, int] = {}
                for t in tokens:
                    tf[t] = tf.get(t, 0) + 1
                doc = Doc(
                    node_id=f.stem,
                    node_type=node_type,
                    title=title,
                    body=body,
                    snippet=self._make_snippet(body, title),
                    confidence=confidence,
                    tokens=tokens,
                    tf=tf,
                    length=len(tokens),
                )
                self._docs.append(doc)
                self._doc_by_id[doc.node_id] = doc

        # 2. Compute IDF + avgdl for BM25
        n = len(self._docs)
        if n == 0:
            self._idf = {}
            self._avgdl = 0.0
        else:
            df: dict[str, int] = {}
            total_len = 0
            for doc in self._docs:
                total_len += doc.length
                for term in doc.tf.keys():
                    df[term] = df.get(term, 0) + 1
            self._avgdl = total_len / n if n else 0.0
            self._idf = {
                term: math.log((n - df_t + 0.5) / (df_t + 0.5) + 1.0)
                for term, df_t in df.items()
            }

        # 3. Build edge adjacency for graph walk
        graph = self.graph_service.build_graph()
        adj: dict[str, set[str]] = {}
        for e in graph.edges:
            adj.setdefault(e.source, set()).add(e.target)
            adj.setdefault(e.target, set()).add(e.source)
        self._edges_by_node = adj

        logger.info(
            "Retrieval index: %d docs, avgdl=%.1f, vocab=%d, edges=%d",
            n, self._avgdl, len(self._idf), sum(len(v) for v in adj.values()),
        )

    def _make_snippet(self, body: str, title: str) -> str:
        text = (body or "").strip().replace("\n", " ")
        text = re.sub(r"\s+", " ", text)
        if not text:
            return title
        return text[:240] + ("..." if len(text) > 240 else "")

    # ------------------------------------------------------------------
    # BM25 scoring
    # ------------------------------------------------------------------

    def _bm25_score(self, query_terms: list[str], doc: Doc) -> float:
        if not query_terms or doc.length == 0 or self._avgdl == 0.0:
            return 0.0
        score = 0.0
        for term in query_terms:
            if term not in self._idf:
                continue
            tf = doc.tf.get(term, 0)
            if tf == 0:
                continue
            idf = self._idf[term]
            denom = tf + BM25_K1 * (1 - BM25_B + BM25_B * (doc.length / self._avgdl))
            score += idf * (tf * (BM25_K1 + 1)) / denom
        return score

    def _bm25_search(self, query: str, top_k: int) -> list[tuple[str, float]]:
        terms = tokenize(query)
        if not terms:
            return []
        scored = [(doc.node_id, self._bm25_score(terms, doc)) for doc in self._docs]
        scored = [s for s in scored if s[1] > 0]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    # ------------------------------------------------------------------
    # Entity seeding + graph walk
    # ------------------------------------------------------------------

    def _extract_seeds(self, query: str, max_seeds: int = 3) -> list[str]:
        """Return up to max_seeds node ids whose slug-form id substring-matches
        query tokens. Matches the longest ids first so 'product management'
        hits 'product-management' rather than two separate matches."""
        q_text = query.lower()
        candidates: list[tuple[int, str]] = []
        for doc in self._docs:
            if doc.node_type == "source":
                continue  # sources usually have noisy episode-title slugs
            id_words = doc.node_id.replace("-", " ")
            if not id_words:
                continue
            # Require the full id (as a phrase) to appear in the query
            if id_words in q_text:
                candidates.append((len(id_words), doc.node_id))
        # Longest match first — prefers specific ids over generic ones
        candidates.sort(reverse=True)
        seen: set[str] = set()
        seeds: list[str] = []
        for _, nid in candidates:
            if nid not in seen:
                seeds.append(nid)
                seen.add(nid)
            if len(seeds) >= max_seeds:
                break
        return seeds

    def _graph_walk(self, seeds: list[str], top_k: int) -> list[tuple[str, float]]:
        """1-hop walk from each seed. Seeds themselves always rank first (the
        user named them), then their neighbors ordered by number of distinct
        seeds that reach them."""
        if not seeds:
            return []
        # Seeds get a dominant score so they always lead the walk ranking.
        # This matters because a phrase-matched concept is the single most
        # confident signal we have that the user cares about that node.
        hit: dict[str, int] = {}
        SEED_WEIGHT = 10_000
        for seed in seeds:
            if seed in self._doc_by_id:
                hit[seed] = SEED_WEIGHT
        for seed in seeds:
            for neighbor in self._edges_by_node.get(seed, set()):
                if neighbor in self._doc_by_id and neighbor not in hit:
                    hit[neighbor] = 0
                if neighbor in self._doc_by_id and hit.get(neighbor, 0) < SEED_WEIGHT:
                    hit[neighbor] = hit.get(neighbor, 0) + 1
        scored = sorted(hit.items(), key=lambda x: x[1], reverse=True)
        return [(nid, float(score)) for nid, score in scored[:top_k]]

    # ------------------------------------------------------------------
    # Fusion + reranking
    # ------------------------------------------------------------------

    @staticmethod
    def _rrf_fuse(*rankings: list[tuple[str, float]]) -> dict[str, float]:
        """Reciprocal rank fusion. Each ranking contributes 1/(k+rank) per
        node. Higher fused score = better."""
        fused: dict[str, float] = {}
        for ranking in rankings:
            for rank, (nid, _score) in enumerate(ranking, start=1):
                fused[nid] = fused.get(nid, 0.0) + 1.0 / (RRF_K + rank)
        return fused

    def _rerank_by_confidence(self, fused: dict[str, float]) -> list[tuple[str, float]]:
        """Scale fused scores by confidence so supported claims outrank
        unsupported ones at similar fused scores. Returns sorted list."""
        out: list[tuple[str, float]] = []
        for nid, base in fused.items():
            doc = self._doc_by_id.get(nid)
            if not doc:
                continue
            multiplier = RERANK_BASE + RERANK_SLOPE * max(0.0, min(1.0, doc.confidence))
            out.append((nid, base * multiplier))
        out.sort(key=lambda x: x[1], reverse=True)
        return out

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def retrieve(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        """Full hybrid pipeline: BM25 + graph walk, RRF-fused, confidence re-ranked."""
        self._ensure_index()
        if not self._docs:
            return []

        bm25 = self._bm25_search(query, top_k=top_k * 2)
        seeds = self._extract_seeds(query)
        walk = self._graph_walk(seeds, top_k=top_k * 2)

        fused = self._rrf_fuse(bm25, walk)
        if not fused:
            return []

        # Direct seed boost: when the query phrase-matches a concept/guest
        # slug, that node should always win over merely co-occurring sources.
        # The bump is ~30x larger than any RRF contribution (max ~2/60), so
        # seeds dominate regardless of BM25 length-normalization quirks.
        for seed in seeds:
            if seed in fused:
                fused[seed] += 1.0

        reranked = self._rerank_by_confidence(fused)[:top_k]

        bm25_rank = {nid: i + 1 for i, (nid, _) in enumerate(bm25)}
        walk_rank = {nid: i + 1 for i, (nid, _) in enumerate(walk)}

        results: list[RetrievalResult] = []
        for nid, score in reranked:
            doc = self._doc_by_id[nid]
            results.append(
                RetrievalResult(
                    node_id=doc.node_id,
                    node_type=doc.node_type,
                    title=doc.title,
                    snippet=doc.snippet,
                    confidence=doc.confidence,
                    score=score,
                    bm25_rank=bm25_rank.get(nid),
                    graph_rank=walk_rank.get(nid),
                )
            )
        return results
