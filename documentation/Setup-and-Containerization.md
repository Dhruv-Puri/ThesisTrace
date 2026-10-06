# Setup & Containerization — Paper2Reality

**Policy (non-negotiable):** nothing is installed globally on anyone's machine.
Everything runs either **inside Docker** (recommended) or inside a **project-local
`.venv`** (development only). No `pip install` outside a venv, no global `npm -g`,
no administrator elevation, no system Python pollution. If a step seems to need a system
install — stop and ask the team; there is always a containerized alternative.

---

## 1. Docker path (recommended — zero host installs)

**Prerequisites:** Docker Desktop (Win/Mac) or Docker Engine (Linux) only.
*(`docker --version` >= 24 with compose v2 — `docker compose version`.)*

```bash
git clone <repo> && cd paper2reality
cp .env.example .env        # optional: paste GEMINI_API_KEY; empty = fully local mode
docker compose up --build
# web UI  -> http://localhost:8080
# API     -> http://localhost:8000/api/health
```

- **First run** downloads base images + Hugging Face weights (~1-2 GB total) into the
  named volume `hf_cache` — subsequent runs are offline. Pre-warm before demo day.
- Everything (API, models, React build) lives in containers. Your host stays clean.
- Stop: `docker compose down` (add `-v` only to wipe the model cache — re-downloads weights).

## 2. Local development path (venv only — for iterating on code)

Use this *only* when you're editing Python/JS frequently; still no global installs.

```bash
# Python side — ALWAYS inside a virtual environment
python3 -m venv .venv                 # project-local, git-ignored
source .venv/bin/activate             # Windows: .venv\Scripts\activate
pip install -r requirements.txt       # safe: pip is now the venv's pip
uvicorn api.main:app --reload

# JS side — project-local only
cd client && npm install              # installs into ./node_modules, never global
npm run dev                           # http://localhost:5173, proxies /api -> :8000
```

Deactivate with `deactivate`. Confirm isolation with `which pip` / `pip -V` — it must
point inside `.venv` before installing anything. **Never** `pip install <pkg>` in a bare
shell; if you did, tell the team (fix: recreate `.venv`).

## 3. Services, ports, volumes

| Service | Build | Port (host->container) | Notes |
|---------|-------|----------------------|-------|
| `api` | `Dockerfile.api` (python:3.11-slim) | 8000 -> 8000 | uvicorn, non-root user `app` |
| `web` | `Dockerfile.web` (node build -> nginx) | 8080 -> 80 | nginx proxies `/api/*` -> `api:8000` |

| Volume | Mount | Purpose |
|--------|-------|---------|
| `hf_cache` | `/models/hf` (api) | Hugging Face weights — downloaded once, survives rebuilds (`HF_HOME=/models/hf`) |
| `api_data` | `/data/uploads` (api) | uploaded PDFs + job results; anonymous volume, never on host |

Environment (via `.env`, see `.env.example`):
`GEMINI_API_KEY` (optional), `LOW_RAM=0|1`, `SEMANTIC=0|1`, `HF_HOME`, `PYTHONUNBUFFERED`.

## 4. Model management (the 1-2 GB reality)

- Models are pinned in `api/pipeline/config.py`; total first-download ~1.0-1.5 GB
  (NER ~250 MB, MNLI ~270 MB, DistilBART ~1.2 GB **or** flan-t5-small ~300 MB in LOW_RAM).
  See the table in [Feasibility-Analysis.md](Feasibility-Analysis.md) section 3.
- Warm the cache once: `docker compose run --rm api python -m pipeline.warmup`
  (downloads everything into `hf_cache`).
- Demo machine: build + warmup **the night before** (venue Wi-Fi is the classic failure).
- To switch models later, edit `config.py` only — never hardcode model names in stages.

## 5. Troubleshooting

| Symptom | Fix |
|---------|-----|
| Port already in use | change host side only: `"8081:80"` in compose |
| First `up` very slow / stuck | image pulls + weight download; check `docker compose logs api` |
| SSL / proxy errors behind college network | set `HF_HUB_OFFLINE=1` after warmup; or pre-copy volume |
| OOM / killed process | `LOW_RAM=1` in `.env`, recreate: `docker compose up -d` |
| Gemini 429 (rate limit) | expected on free tier — app auto-falls back to templates |
| Frontend can't reach API | nginx proxies in prod path; in dev, Vite proxy on 5173 (check `vite.config.js`) |
| `.venv` confusion / weird package errors | delete and recreate `.venv` (your machine, your venv — that is allowed) |

## 6. What never goes on anyone's host machine

System-wide pip packages · global npm packages · model weights outside the `hf_cache`
volume · database servers (we don't need one) · administrator/root commands. If a future
feature seems to need these, it needs a new container instead.
