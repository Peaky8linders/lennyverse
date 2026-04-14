# LennyVerse

**The living knowledge graph of product management wisdom.**

A zoomable, pannable canvas mapping every concept, framework, and debate from Lenny's Newsletter and Podcast. Built on Karpathy's LLM wiki pattern and graphify's extraction pipeline.

![Stack: Vite + React 18 + TypeScript + Tailwind + React Flow + Framer Motion | FastAPI + Python 3.12 + Claude API](https://img.shields.io/badge/stack-vite%20%7C%20react%20%7C%20fastapi%20%7C%20claude-blue)

## What it does

- **131 nodes** auto-extracted from Lenny's free starter pack: 50 real guests, 19 frameworks/concepts, 62 episodes
- **180 edges** connecting guests → concepts → episodes (`teaches`, `mentioned_in`, `builds_on`, `appears_in`)
- **Click any guest** → side panel opens with their episode cards, each a purple gradient link that opens the real Lenny's Substack URL in a new tab
- **Click any concept** → see which guests teach it, related concepts, and contradictions
- **Ask Claude** → grounded Q&A over the compiled wiki, streamed via SSE

## Architecture

Three layers, following [Andrej Karpathy's LLM Knowledge Base pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f):

```
knowledge/raw/          immutable input — Lenny's free starter pack (gitignored per license)
  ├─ newsletters/       10 posts
  ├─ podcasts/          50 transcripts
  └─ index.json         metadata (titles, guests, dates, descriptions)

knowledge/wiki/         LLM-compiled knowledge pages (gitignored)
  ├─ concepts/          one .md per concept with frontmatter
  ├─ guests/            one .md per guest
  ├─ sources/           one .md per episode with Lenny URL
  ├─ domains/           one .md per domain cluster
  ├─ tensions/          contradiction pages
  ├─ index.md           master catalog
  └─ log.md             chronological ingestion log

schema.md               compilation rules, node types, edge types
```

The compiler runs three passes, inspired by [graphify](https://github.com/safishamsi/graphify):

1. **Structure extraction** (deterministic) — parses `index.json` for titles, guests, dates, and pulls concept topics from `covering X, Y, Z` patterns in episode descriptions
2. **Semantic extraction** (optional, Claude or Ollama) — extracts frameworks, relationships, tensions from transcripts
3. **Community detection** (Leiden clustering on `python-igraph`) — auto-discovers domain clusters from edge topology

## Quick start

### Prerequisites

- Python 3.12
- Node.js 20+
- (Optional) Anthropic API key for semantic extraction + Q&A

### 1. Download Lenny's starter pack

Lenny's license forbids redistributing the raw data, so you download it yourself:

```bash
git clone https://github.com/LennysNewsletter/lennys-newsletterpodcastdata /tmp/lennys-data
```

Or visit [lennysdata.com](https://www.lennysdata.com) for a zip.

### 2. Install backend + seed the data

```bash
cd lennyverse/backend
pip install -r requirements.txt
cd ..
python scripts/seed_raw.py /tmp/lennys-data
```

### 3. Compile the wiki

```bash
# Without API key (structural + description-based extraction, instant)
python scripts/compile.py

# With Claude semantic extraction (recommended, richer graph, ~60s)
ANTHROPIC_API_KEY=sk-... python scripts/compile.py
```

Output: ~130 nodes, ~180 edges, written to `knowledge/wiki/`.

### 4. Run the app

**Backend** (port 8080):

```bash
cd lennyverse/backend
uvicorn app.main:app --reload --port 8080
```

**Frontend** (port 5173):

```bash
cd lennyverse/frontend
npm install
npm run dev
```

Open http://localhost:5173.

## API

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/graph` | Full compiled knowledge graph (nodes + edges + domains) |
| `GET` | `/api/node/{id}` | Detailed info for a single node (wiki content + connections) |
| `POST` | `/api/explore` | Claude Q&A grounded in the wiki (SSE streaming) |
| `POST` | `/api/ingest` | Add new content — LLM auto-wires into the graph |
| `GET` | `/api/report` | `GRAPH_REPORT.md` — god nodes, surprising connections |
| `GET` | `/health` | Status + wiki state |

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | — | Claude API for compilation + Q&A (optional) |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama fallback endpoint |
| `OLLAMA_MODEL` | `llama3.2:3b` | Ollama model |
| `COMPILE_MODEL` | `claude-sonnet-4-6-20250514` | Claude model for compilation |
| `EXPLORE_MODEL` | `claude-sonnet-4-6-20250514` | Claude model for Q&A |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed frontend origins (comma-separated) |
| `PORT` | `8080` | Backend port |
| `RATE_LIMIT` | `10/minute` | SlowAPI rate limit per IP |
| `WIKI_PATH` | `./knowledge/wiki` | Compiled wiki location |
| `RAW_PATH` | `./knowledge/raw` | Raw dataset location |

## Deployment

**Backend (Railway):**

```bash
railway up
railway variables set ANTHROPIC_API_KEY=sk-...
railway variables set CORS_ORIGINS=https://your-frontend.vercel.app
```

Railway picks up `railway.toml` + `Dockerfile` automatically.

**Frontend (Vercel):**

```bash
cd frontend
vercel deploy
```

Set `BACKEND_URL` env var to your Railway URL. `vercel.json` handles the `/api/*` rewrite.

## License

This project's source code is MIT.

Lenny's Newsletter/Podcast dataset is **not redistributed** here — users must download it themselves from the official repo, and its use is governed by [Lenny's starter-dataset license](https://github.com/LennysNewsletter/lennys-newsletterpodcastdata/blob/main/LICENSE.md).

## Credits

- [Andrej Karpathy's LLM Knowledge Base gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) for the wiki architecture
- [graphify](https://github.com/safishamsi/graphify) for the 3-pass extraction pattern
- [Lenny Rachitsky](https://www.lennysnewsletter.com) for releasing the dataset
