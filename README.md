# LennyVerse

**The living knowledge graph of product management wisdom.**

A zoomable, pannable canvas mapping every concept, framework, and debate from Lenny's Newsletter and Podcast. Built on Karpathy's LLM wiki pattern and graphify's extraction pipeline.

![Stack: Vite + React 18 + TypeScript + Tailwind + React Flow + Framer Motion | FastAPI + Python 3.12 + Claude API](https://img.shields.io/badge/stack-vite%20%7C%20react%20%7C%20fastapi%20%7C%20claude-blue)

## What it does

- **Real guest headshots on every node** — pulled from Lenny's podcast RSS feed (`api.substack.com/feed/podcast/10845.rss`). Each `<itunes:image>` contains the guest's face, so `scripts/fetch_guest_images.py` slugifies 286 guests and hotlinks 338 episode covers straight from Substack's CDN. (Same trick [LennyRPG](https://www.lennysnewsletter.com/p/how-i-built-lennyrpg) used for its avatars.)
- **131 nodes** auto-extracted from Lenny's free starter pack: 50 real guests, 19 frameworks/concepts, 62 episodes
- **180 edges** connecting guests → concepts → episodes (`teaches`, `mentioned_in`, `builds_on`, `appears_in`)
- **Click any guest** → side panel opens with their episode cards, each showing the real episode cover art and linking to Lenny's Substack post
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

- **Python 3.12**
- **Node.js 20+**
- **One LLM backend** (pick any in [LLM backends](#llm-backends)):
  - Anthropic Claude API key (richest graph, ~60s compile), **or**
  - Local [Ollama](https://ollama.com) (free, private, CPU-bound), **or**
  - Nothing at all — the fast structural compile (`compile_fast.py`) skips the semantic pass entirely

### 1. Clone and install

```bash
git clone https://github.com/Peaky8linders/lennyverse
cd lennyverse

# Backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt

# Frontend
cd frontend && npm install && cd ..
```

### 2. Get Lenny's starter pack

Lenny's license forbids redistributing the raw data, so you download it yourself:

```bash
git clone https://github.com/LennysNewsletter/lennys-newsletterpodcastdata /tmp/lennys-data
python scripts/seed_raw.py /tmp/lennys-data
```

This copies 50 podcast transcripts + 10 newsletter posts + `index.json` into `knowledge/raw/`.

### 3. Fetch guest headshots (one-time, ~5s)

```bash
python scripts/fetch_guest_images.py
```

Pulls Lenny's podcast RSS feed, maps 286 guests and 338 episodes to their cover-art URLs, and writes `frontend/public/guest_images.json` + `episode_images.json`. These are what the graph nodes and episode cards render.

### 4. Compile the wiki

Pick one of the three paths below — see [LLM backends](#llm-backends) for the full story:

```bash
# A) No LLM — structural + description-based extraction (~2s, ~130 nodes)
python scripts/compile_fast.py

# B) Anthropic Claude — full 3-pass compile with semantic extraction (~60s, richer graph)
ANTHROPIC_API_KEY=sk-... python scripts/compile.py

# C) Local Ollama — same 3-pass compile, routed to llama3.2:3b on localhost
python scripts/compile.py
```

Output goes to `knowledge/wiki/` (concepts, guests, sources, domains, tensions).

### 5. Run the app

Two terminals:

```bash
# Terminal 1 — backend on :8080
cd backend
uvicorn app.main:app --reload --port 8080

# Terminal 2 — frontend on :5173
cd frontend
npm run dev
```

Open **http://localhost:5173**. If 5173 is busy, Vite falls through to 5174. Vite's dev server proxies `/api/*` to the backend on `127.0.0.1:8080`, so you don't need to set any URL env vars for local dev.

## Usage

Once both servers are up:

- **Pan** — drag the canvas background
- **Zoom** — mouse wheel, or the `+` / `−` buttons in the bottom-right controls
- **Fit view** — click the fit icon in the controls (useful after you've zoomed around)
- **Search** — top-left search bar filters guests and concepts by name; hit a result to jump to it
- **Minimap** — bottom-right overview for orientation on larger graphs
- **Click a guest node** → the detail panel slides in from the right with their `known_for` list and a gallery of episode cards. Each card has the real episode cover as a thumbnail and opens the episode on `lennysnewsletter.com` in a new tab.
- **Click a concept node** → the detail panel shows which guests teach it, the domain it belongs to, related concepts, and any `contrasts_with` tensions
- **Ask Claude** — bottom-right of the detail panel. Type a question grounded in the currently-selected node; answers stream via SSE from `/api/explore` and cite the wiki pages they're drawn from. Requires an LLM backend (Anthropic or Ollama).
- **Deep-link a zoomed sub-graph** — append `?focus=<slug1>,<slug2>,...` to the URL and the canvas fits only those nodes on load. Useful for sharing views:
  ```
  http://localhost:5173/?focus=keith-rabois,claire-vo,simon-willison,boris-cherny
  ```

## LLM backends

LennyVerse's compiler and `/api/explore` endpoint use `backend/app/services/llm_client.py`, which picks a backend at runtime based on env vars:

| You set | Backend used | Fallback when unreachable |
|---|---|---|
| `ANTHROPIC_API_KEY` | Anthropic Claude | _none — fails fast_ |
| _(nothing)_ | Ollama at `$OLLAMA_URL` | _none — skip semantic extraction_ |

### Option A — Anthropic Claude (fastest + richest)

```bash
export ANTHROPIC_API_KEY=sk-...
python scripts/compile.py          # full 3-pass compile, ~60s
cd backend && uvicorn app.main:app --reload --port 8080
```

Compilation runs 5 files in parallel, `/api/explore` Q&A uses `claude-sonnet-4-6-20250514` by default. Override the model IDs via `COMPILE_MODEL` / `EXPLORE_MODEL` if you want to pin something else.

### Option B — Ollama (local, free, slow on CPU)

1. **Install Ollama** — https://ollama.com (macOS, Linux, Windows). It auto-starts a daemon at `http://localhost:11434`.
2. **Pull the default model** (other models work too — see `OLLAMA_MODEL`):
   ```bash
   ollama pull llama3.2:3b
   ```
3. **Sanity check** — `curl http://localhost:11434/api/tags` should list `llama3.2:3b`.
4. **Compile** with no `ANTHROPIC_API_KEY` in the environment:
   ```bash
   unset ANTHROPIC_API_KEY                 # make sure the Anthropic path is disabled
   python scripts/compile.py
   ```
   The compiler drops to `concurrency=1` for Ollama (one request at a time) and truncates transcripts to 6000 chars to fit the model's context. On a CPU, expect **~5–15 minutes** for the 60-file starter pack with `llama3.2:3b`. A larger model (`qwen3:30b-a3b`, `llama3.1:8b`) gives better concepts but takes longer.
5. **Run the backend** — same command as Option A. `/api/explore` Q&A will also use Ollama, which is plenty fast for single-question streaming.

Point at a different Ollama host or model via env vars:

```bash
export OLLAMA_URL=http://192.168.1.10:11434
export OLLAMA_MODEL=qwen3:30b-a3b
python scripts/compile.py
```

### Option C — No LLM at all (fastest bootstrap)

```bash
python scripts/compile_fast.py
```

This runs **Pass 1** (structural extraction from `index.json`) and **Pass 3** (Leiden community detection) only, skipping the semantic LLM pass. You get ~130 nodes and ~180 edges in ~2 seconds — enough to populate the canvas and see the guest arc light up with real headshots. `/api/explore` will return an error without a configured LLM backend, but the graph and detail panel work fully.

## Troubleshooting

### "Make sure the backend is running and the wiki has been compiled"

The frontend shows this when `GET /api/graph` fails or returns zero nodes. Three common causes:

1. **Backend isn't running.** `curl http://127.0.0.1:8080/health` — you should get JSON with `"status": "ok"`. If not, start `uvicorn app.main:app --reload --port 8080` from `backend/`.
2. **Wiki is empty.** If `/health` returns `"concept_count": 0`, you haven't compiled yet. Run `python scripts/compile_fast.py` (or one of the other compile paths — see [LLM backends](#llm-backends)).
3. **Port mismatch.** Vite proxies `/api/*` to `127.0.0.1:8080` — if you changed the backend port, also update `frontend/vite.config.ts` or set `VITE_API_URL` in `frontend/.env`.

### Graph loads but every guest shows initials instead of a headshot

You haven't run the one-time image fetch:

```bash
python scripts/fetch_guest_images.py
```

This writes `frontend/public/guest_images.json` + `episode_images.json`. Vite serves them as static assets, so restart the dev server after the first run to clear its in-memory cache. Confirm with `curl http://localhost:5173/guest_images.json | head` — you should see real `substackcdn.com` URLs.

If the JSON is present but images still don't render, open DevTools → Network → filter on `substackcdn` and look for blocked requests. Some corporate proxies strip the `Referer` header, which Substack's CDN occasionally rejects; in that case point `frontend/public/guest_images.json` at a local mirror by downloading the images into `frontend/public/avatars/` and rewriting the URLs.

### Backend returns `500 Internal Server Error` on `/api/graph`

Check the uvicorn log — the global exception handler logs the real cause with `exc_info=True`. The three failures we've hit:

1. **Wiki directory missing.** The compile never produced `knowledge/wiki/`. Fix: run a compile script.
2. **Malformed YAML frontmatter.** A hand-edited wiki page has broken `---` delimiters. Fix: delete the offending file and recompile, or run `py -3.12 -c "from app.services.frontmatter import read_wiki_page; print(read_wiki_page('path/to/file.md'))"` to pin down the parser error.
3. **`ANTHROPIC_API_KEY` set to an invalid string** (like the word "none"). The `/api/explore` endpoint then tries Anthropic and 401s. Fix: `unset ANTHROPIC_API_KEY` to fall through to Ollama, or set a real key.

### Ollama compile hangs or times out

A few things to rule out:

- **Is the daemon actually up?** `curl http://localhost:11434/api/tags` should list models. If it hangs, start Ollama (macOS/Windows: launch the app; Linux: `systemctl --user start ollama` or `ollama serve`).
- **Is the model pulled?** `ollama list` — if `llama3.2:3b` isn't there, run `ollama pull llama3.2:3b`.
- **CPU-only is slow.** With no GPU, each file takes 30–90 seconds and the compiler runs `concurrency=1`, so 60 files can easily take **10+ minutes**. Watch `curl http://localhost:11434/api/ps` — as long as a model is listed and `size_vram > 0` (GPU) or the process CPU is pegged, it's working. If you want proof of progress mid-run, `tail -f` the uvicorn log; the compiler emits one `INFO` line per file.
- **Prefer a smaller context.** `OLLAMA_MODEL=llama3.2:1b` trades quality for ~3× throughput.
- **Just want the graph and not the semantic concepts?** Switch to `scripts/compile_fast.py` — it skips Ollama entirely.

### `Port 5173 is in use, trying another one…`

Vite automatically falls through to 5174, 5175, etc. The README uses `5173` everywhere for clarity, but open the actual URL Vite prints at startup. The `/api` proxy still works on the fallback port.

### CORS errors in the browser console

Dev mode allows `*` — if you see a CORS error, you're probably running the backend in production mode (`ENV=production`) without adding the frontend URL to `CORS_ORIGINS`. Either unset `ENV` or run:

```bash
export CORS_ORIGINS=http://localhost:5173,http://localhost:5174
```

### The `?focus=slug1,slug2` deep link doesn't zoom

Three things to check:

1. The slugs match the IDs React Flow renders. Open DevTools console and run `Array.from(document.querySelectorAll('.react-flow__node')).map(n=>n.getAttribute('data-id'))` — every slug you pass must appear in that list.
2. The slugs are **not** URL-encoded. Pass `?focus=keith-rabois,claire-vo`, not `?focus=keith-rabois%2Cclaire-vo`.
3. You're on the canvas root URL (`/`) and not on an initial-hash route. The logic runs once inside `GraphCanvas.tsx`'s mount effect 750ms after the graph loads.

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
