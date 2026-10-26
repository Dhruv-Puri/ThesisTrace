# Setup & Containerization — Paper2Reality

**Policy (non-negotiable):** nothing is installed globally on anyone's machine.
Everything runs either **inside Docker** (recommended) or inside a **project-local
`.venv`** (development only). No `pip install` outside a venv, no global `npm -g`,
no administrator elevation, no system Python pollution. If a step seems to need a system
install — stop and ask the team; there is always a containerized alternative.

**Everything this project writes stays in this folder.** Uploads, job output and the
Hugging Face model cache live in `./.data/` (git-ignored), bind-mounted into the
containers. Delete that folder — or the whole project — and nothing is left behind
except the Docker images themselves (removed with the command in §3).

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

- **First run** downloads base images + Hugging Face weights (~1-2 GB total) into
  `./.data/hf` — subsequent runs are offline. Pre-warm before demo day.
- Everything (API, models, React build) lives in containers. Your host stays clean;
  the only project state is the local `.data/` folder.
- Stop: `docker compose down`. This leaves `.data/` intact (next start is fast).

## 2. Local development path (venv only — for iterating on code)

Use this *only* when you're editing Python/JS frequently; still no global installs.

```bash
# Python side — ALWAYS inside a virtual environment
python3 -m venv .venv                 # project-local, git-ignored
source .venv/bin/activate             # Windows: .venv\Scripts\activate
export PIP_CACHE_DIR="$PWD/.data/pip-cache"
pip install --no-cache-dir -r requirements.txt   # venv's pip, no user cache
PIP_NO_CACHE_DIR=1 python -m spacy download en_core_web_sm
uvicorn api.main:app --reload

# JS side — project-local only
cd client
npm_config_cache=../.data/npm-cache npm install --no-audit --no-fund
npm run dev                           # http://localhost:5173, proxies /api -> :8000
```

The cache variables keep pip/npm downloads in `.data/` instead of your home folder;
the venv and `node_modules` are inside the repo. The app's own default `HF_HOME` is
`.data/hf` (see `api/pipeline/config.py`), so even local model downloads stay here.

Deactivate with `deactivate`. Confirm isolation with `which pip` / `pip -V` — it must
point inside `.venv` before installing anything. **Never** `pip install <pkg>` in a bare
shell; if you did, tell the team (fix: recreate `.venv`).

## 3. Services, ports, volumes

| Service | Build | Port (host->container) | Notes |
|---------|-------|----------------------|-------|
| `api` | `Dockerfile.api` (python:3.11-slim) | 8000 -> 8000 | uvicorn, non-root user `app` |
| `web` | `Dockerfile.web` (node build -> nginx) | 8080 -> 80 | nginx proxies `/api/*` -> `api:8000` |

| Host folder | Container mount | Purpose |
|-------------|-----------------|---------|
| `./.data/hf` | `/models/hf` (api) | Hugging Face weights — downloaded once, survives rebuilds (`HF_HOME=/models/hf`) |
| `./.data` | `/data` (api) | data root; uploads land in `.data/uploads` |

Both are **bind mounts inside this repository**, not Docker named volumes, so there is
no hidden state elsewhere. Locally (without Docker) the API uses the same `.data/uploads`
default; set `P2R_DATA_DIR` only if you deliberately want another path — remember that
points outside the project. Deleting `.data/` removes every upload, result and model this
project downloaded.

Full cleanup (also removes the two locally built images and their build cache):

```bash
docker compose down --rmi local
rm -rf .data
```

Docker itself stores its images and build cache in its own program-data directory; that
is the one thing a containerized project cannot place inside the repo. The command above
removes the images this project built. Nothing is installed system-wide (no pip/npm
package, no service, no scheduled task).

Environment (via `.env`, see `.env.example`):
`GEMINI_API_KEY` (optional), `LOW_RAM=0|1`, `SEMANTIC=0|1`, `HF_HOME`, `PYTHONUNBUFFERED`.

## 4. Model management (the 1-2 GB reality)

- Models are pinned in `api/pipeline/config.py`; total first-download ~1.0-1.5 GB
  (NER ~250 MB, MNLI ~270 MB, DistilBART ~1.2 GB **or** flan-t5-small ~300 MB in LOW_RAM).
  See the table in [Feasibility-Analysis.md](Feasibility-Analysis.md) section 3.
- Warm the cache once: `docker compose run --rm api python -m api.pipeline.warmup`
  (downloads everything into `.data/hf`).
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

System-wide pip packages · global npm packages · model weights outside `.data/hf` ·
files outside this repository · database servers (we don't need one) · administrator/root
commands. The containers themselves run as a non-root user after the entrypoint fixes
ownership of the bind-mounted `.data/` folders. If a future feature seems to need
anything on this list, it needs a new container instead.
