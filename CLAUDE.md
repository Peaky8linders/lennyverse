# LennyVerse — Claude Code Instructions

Living knowledge graph of product management wisdom, compiled from Lenny's Newsletter + Podcast starter pack. Zoomable React Flow canvas over a FastAPI-served graph, with Claude-grounded Q&A.

## Stack

**Backend** (`backend/`) — Python 3.12, FastAPI, Anthropic SDK, SlowAPI, python-igraph + leidenalg (Leiden community detection), PyYAML, httpx, pydantic v2. Tests via pytest + pytest-asyncio.

**Frontend** (`frontend/`) — Vite 6 + React 18 + TypeScript 5.6, `@xyflow/react` (React Flow v12), Framer Motion, Tailwind 3. No test harness yet.

**Compilation** (`scripts/`) — `seed_raw.py`, `compile.py`, `fetch_urls.py`. Claude API for semantic pass, Ollama (`llama3.2:3b`) as fallback.

## Layout

```
backend/app/
  main.py              FastAPI factory, CORS, SlowAPI, global error handler, /health
  config.py            env-driven config singleton (cors_origins, wiki_path, models, ...)
  models.py            pydantic response/request models
  rate_limit.py        SlowAPI limiter (default 10/minute per IP)
  routers/
    graph.py           GET /api/graph, GET /api/node/{id}, GET /api/report
    explore.py         POST /api/explore — Claude SSE streaming Q&A
    ingest.py          POST /api/ingest — add content, LLM auto-wires into graph
  services/
    compiler.py        3-pass compile (structure → semantic → Leiden clustering)
    frontmatter.py     YAML frontmatter read/write for wiki .md pages
    graph_service.py   build in-memory graph from wiki frontmatter
    llm_client.py      Anthropic + Ollama client with fallback
  tests/               pytest suite (frontmatter, graph_service)

frontend/src/
  App.tsx              top-level layout: canvas + search + detail panel + ask-claude
  components/          GraphCanvas, ConceptNode, GuestNode, TensionEdge, DetailPanel,
                       SearchBar, DomainFilters, AskClaude
  hooks/               useGraph (fetches /api/graph), useExplore (SSE to /api/explore)
  types/graph.ts       shared node/edge types

knowledge/
  raw/                 gitignored — Lenny's starter pack (license forbids redistribution)
  wiki/                gitignored — compiled output (concepts, guests, sources, domains, tensions)
  schema.md            compilation rules, node types, edge types

scripts/
  seed_raw.py          copy starter pack into knowledge/raw/
  compile.py           run 3-pass pipeline → knowledge/wiki/
  fetch_urls.py        resolve real Substack post URLs for episodes
```

## Commands

**Backend dev:**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
pytest                           # run tests
```

**Frontend dev:**
```bash
cd frontend
npm install
npm run dev                      # Vite on :5173
npm run build                    # tsc -b && vite build
```

**Full pipeline from raw data:**
```bash
git clone https://github.com/LennysNewsletter/lennys-newsletterpodcastdata /tmp/lennys-data
python scripts/seed_raw.py /tmp/lennys-data
ANTHROPIC_API_KEY=sk-... python scripts/compile.py    # ~60s, richer graph
# or omit the key for structural-only compile (instant)
```

## Environment variables

| Var | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Compilation semantic pass + /api/explore Q&A |
| `OLLAMA_URL` | `http://localhost:11434` | Local fallback when no Anthropic key |
| `OLLAMA_MODEL` | `llama3.2:3b` | — |
| `COMPILE_MODEL` / `EXPLORE_MODEL` | `claude-sonnet-4-6-20250514` | Override per-phase |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated; enforced only in prod |
| `PORT` | `8080` | Backend port |
| `RATE_LIMIT` | `10/minute` | Per-IP SlowAPI limit |
| `WIKI_PATH` / `RAW_PATH` | `./knowledge/wiki`, `./knowledge/raw` | — |

## Conventions

- **No raw-data commits.** `knowledge/raw/` and compiled `knowledge/wiki/` are gitignored per Lenny's license. Never add them back. Check `.gitignore` before committing anything under `knowledge/`.
- **Model IDs.** Default to `claude-sonnet-4-6-20250514` via `config.COMPILE_MODEL` / `EXPLORE_MODEL` env vars — don't hardcode model strings elsewhere.
- **LLM fallback order** in `services/llm_client.py`: Anthropic if key present → Ollama → raise. Keep this contract when editing.
- **Wiki pages are the source of truth** for the graph. `graph_service.py` builds the in-memory graph by reading frontmatter from `knowledge/wiki/`. Don't bypass frontmatter when adding new node types — update `schema.md` and `frontmatter.py` instead.
- **Edge types** defined in `schema.md`: `teaches`, `mentioned_in`, `builds_on`, `appears_in`, plus tension/contradiction edges. New edge types require a schema update.
- **Routers stay thin.** Business logic goes in `services/`. Routers handle pydantic I/O, rate limiting, SSE framing.
- **Frontend node components** (`ConceptNode.tsx`, `GuestNode.tsx`) are React Flow custom nodes — update `nodeTypes` in `GraphCanvas.tsx` when adding a new kind.
- **Production gate:** `create_app()` exits if `ANTHROPIC_API_KEY` is unset in prod. Don't relax this.
- **CORS** is wide-open (`*`) in dev, restricted to `config.cors_origins` in prod. Preserve that split.

## Deployment

- **Backend → Railway.** `backend/Dockerfile` + `backend/railway.toml`. Set `ANTHROPIC_API_KEY` and `CORS_ORIGINS` via `railway variables set`.
- **Frontend → Vercel.** `frontend/vercel.json` rewrites `/api/*` to `BACKEND_URL`.

## Gotchas

- **Real Lenny URLs** are resolved via the Substack post API in `scripts/fetch_urls.py` — don't construct URLs from slugs, they 404. See commit `97f73c5`.
- **React Flow edge measurement:** edges won't render until nodes report dimensions. `GraphCanvas` force-measures on mount — preserve that (see commit `692fd46`).
- **Source ID collisions** were a past bug (`97f73c5`); keep source IDs prefixed/namespaced by type when extending the compiler.
- **Leiden clustering** runs on `python-igraph`, not networkx. Community labels are non-deterministic across runs — don't assert exact labels in tests, assert structure.

## Testing

- Backend: `cd backend && pytest`. Tests live in `backend/tests/`, cover frontmatter and graph_service.
- Frontend: no test runner configured. UI changes need manual verification via `npm run dev`.
- Before claiming completion on compiler/graph changes, run `python scripts/compile.py` against a seeded `knowledge/raw/` and confirm node/edge counts in `/health` + `/api/graph`.
