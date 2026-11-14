# Production Readiness

**Verdict:** demo-ready and single-host pilot-ready. Not multi-tenant SaaS. The difference
is authentication, isolation and operations, listed honestly below.

---

## 1. What is shipped

| Area | State | Evidence |
|---|---|---|
| API | FastAPI, typed errors, CORS allowlist, upload caps | `api/main.py` |
| Durable queue | SQLite, atomic claim, leases, fencing, retries, bounded queue | `api/jobs/store.py` |
| Retention | Upload TTL 1 h, result TTL 24 h, max 200 stored jobs, janitor | `api/jobs/cleanup.py` |
| Input safety | 30 MB / 60 pages, `%PDF` magic check, filename sanitisation, extension allowlist | `api/main.py` |
| Prompt injection | instruction-like lines detected and excluded from prompts/evidence | `api/pipeline/textutils.py`, tests |
| Grounding | citation filter, numeric hallucination check, verbatim claim check | `api/pipeline/report.py`, tests |
| Audit trail | per-claim receipt: retrieval scores, NLI probabilities, thresholds, model, version, timestamp | `api/pipeline/evidence.py`, `GET /api/jobs/{id}/audit` |
| Portfolio | readiness table + shared-claim ledger, stored under `.data/portfolios` | `api/pipeline/portfolio.py` |
| Tests | 139 stdlib tests; queue, injection, report, TRL, evidence, portfolio | `python -m unittest discover -s api/tests -t .` |
| Packaging | CPU-only Docker API, nginx web image, compose, project-local `.data` | `Dockerfile.*`, `docker-compose.yml` |
| UI | 4 tabs + portfolio, no external assets, self-hosted fonts | `client/src` |

---

## 2. What is not shipped

| Gap | Consequence | Needed for |
|---|---|---|
| No authentication | Anyone with the URL can upload and read jobs | Public deployment |
| No per-user quotas | One user can fill the queue | Paid tiers |
| No multi-tenant isolation | Jobs are visible to anyone who knows an id | Institutional use |
| No metrics/tracing export | Only logs and `/api/health` | On-call operation |
| No automated backup | SQLite file must be copied manually | Pilot data safety |
| No CI pipeline | Tests run by hand | Team reliability |
| Model tier never timed on this host | Latency/RAM numbers are fallback-only | Performance claims |
| No TLS/reverse proxy in compose | HTTP only on localhost | Any network deployment |

Do not call the product "production ready" without resolving at least authentication,
quotas, backup and TLS.

---

## 3. Service levels for a pilot

| SLI | Target | Current |
|---|---|---|
| API availability (pilot hours) | 99% | Single host, no redundancy |
| Analysis p95, fallback tier | < 5 s | ~16 ms per corpus paper, measured |
| Analysis p95, model tier | < 60 s | Not measured |
| Queue wait | < 60 s at 1 worker | Visible in `/api/health` |
| Error rate | < 2% of jobs | Covered by retries + `WORKER_LOST` |
| Data retention | Uploads 1 h, results 24 h | Implemented |

State the tier when quoting a latency. A fallback number is not a model number.

---

## 4. Security and privacy

**Threat model:** hostile PDFs, prompt injection inside documents, oversized uploads,
path traversal in filenames, queue exhaustion, accidental public exposure, data retention.

Controls already present:

- The document is treated as untrusted data; instruction-like lines are excluded from
  evidence and prompts, and the prompt templates fence the text.
- A `.pdf` must start with `%PDF`; uploads are capped at 30 MB and 60 pages.
- Filenames are reduced to a basename; uploads are written under a job id inside `.data`.
- CORS allows only localhost origins; there is no wildcard.
- No external calls unless a Gemini key is set; with a key, only the question and retrieved
  passages are sent, never the file.
- Reports drop sentences without a valid `[p.N]`; claims must be verbatim in the source.

For a pilot, add: authentication in front of the API, TLS, a per-key quota, and an explicit
data-processing note for participants.

---

## 5. Operations runbook

```bash
# start (local)
docker compose up --build

# health and queue
curl /api/health

# warm the model cache before a demo
docker compose run --rm api python -m api.pipeline.warmup

# run tests
python -B -m unittest discover -s api/tests -t . -v

# back up the queue and results (stop the API first for a consistent copy)
cp .data/jobs.sqlite3 .data/backup-jobs.sqlite3

# rotate logs / free disk: delete old uploads
rm -rf .data/uploads/*
```

Logs: `api` container stdout, plus `.data/api.log` in the local run. The job id is the
correlation key from upload to audit.

Failure playbook:

| Symptom | Check | Action |
|---|---|---|
| Jobs stuck queued | `/api/health` queue counts | Restart API; leases expire and jobs retry |
| Model load slow/OOM | logs, `LOW_RAM` | Set `LOW_RAM=1`; the pipeline degrades |
| Disk full | `.data` size | Lower result TTL; clear uploads and model cache |
| Bad PDF | job error `NO_SENTENCES` | Ask for a text version; OCR is out of scope |
| 503 on upload | queue at capacity | Wait for `Retry-After`; raise workers only with RAM |

---

## 6. Deployment options

| Option | Fit | Notes |
|---|---|---|
| Local Docker on a laptop | Demo, viva | Primary path; no network exposure |
| Lab VM (4 vCPU, 8 GB) | Pilot | Add TLS and auth; models optional |
| Self-hosted institutional | Later | Same image, private network |
| Static demo build | Marketing only | No API, fixture data |

Freebuff Sites/Workers cannot host this service: it is a Python + transformers CPU workload,
not a Worker fetch handler. Say this plainly rather than promising a hosted demo that will
not run.

---

## 7. Cost model

| Item | Value | Basis |
|---|---|---|
| Compute per paper, fallback | negligible | 16 ms measured |
| Compute per paper, model tier | ~$0.0006 | 45 s at $0.05/CPU-hour, assumption |
| VM for pilot | $20–$60/month | 4 vCPU / 8 GB, assumption |
| Model storage | ~1–2 GB | Local cache |
| Support | dominant cost | Assumption; see business plan |

Compute is not the constraint. Support and acquisition are.

---

## 8. Pilot go/no-go checklist

- [ ] Authentication and per-user quota in front of the API
- [ ] TLS and a non-localhost origin configured
- [ ] Retention policy communicated to participants
- [ ] Backup taken and a restore tested once
- [ ] Model tier timed on the pilot VM, or `LOW_RAM=1` declared
- [ ] One full analysis from upload to audit file rehearsed
- [ ] Error path tested: corrupt PDF, oversized file, queue full
- [ ] Pilot success metrics agreed in writing

Until every box is ticked, describe the product as a local demo, not a pilot.
