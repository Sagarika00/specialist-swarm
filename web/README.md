# RFP Response Studio — web console

A business-facing UI over the specialist swarm.

## Run

```bash
cd ..                       # repo root
python -m pip install -r requirements.txt -r web/requirements.txt
# swarm must be built once:  setup_environment.py, create_specialists.py,
#                            upload_skills.py, create_coordinator.py
cd web
python -m uvicorn server:app --reload --port 8000
```

Open http://localhost:8000

## What it does

| Feature | Where |
|---|---|
| Paste an RFP, pick **Fast** (markdown, ~5 min) or **Full** (branded .docx) | top bar toggle |
| **Analyze & chat** — register the RFP without running the swarm | input panel |
| **Ask the RFP** — streaming chat grounded in the RFP + specialist verdicts + draft | workspace tab |
| **Instant read** — ~15-sec bid triage: customer, deal size, deadline, red flags, BID / NO-BID | workspace tab |
| **Deal lifecycle** — the full pursuit, what's built vs roadmap | workspace tab |
| Live swarm board — coordinator + 4 specialists, click a specialist for its verdict | centre |
| Live token + cost meter, reconciled with the API's own `session.usage` | right rail |
| **Compliance scan** — secrets / API keys / PII / internal-only leakage | action bar → modal |
| **Proposal viewer** — deliverable rendered in-browser, TOC, auto compliance banner | `/proposal/{sid}` |
| Internal vs client-facing file separation (`INTERNAL_` files flagged, withheld from "download to send") | everywhere |
| **Run history / audit trail** | top bar → History (persisted to `web/.runs.json`) |

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/analyze` | register an RFP (chat + instant read, no swarm) |
| POST | `/api/run` | run the swarm (`session_id` optional — reuses an analyzed one) |
| GET | `/api/stream/{sid}` | SSE — live swarm events + token meter (replay-safe on reconnect) |
| POST | `/api/chat/{sid}` | streaming Q&A over the RFP + analysis |
| POST | `/api/brief/{sid}` | instant read JSON |
| GET | `/api/summary/{sid}` | usage, cost, timings, specialist verdicts |
| GET | `/api/deliverable/{sid}` | client-facing deliverable rendered to HTML |
| GET | `/api/scan/{sid}` | compliance scan |
| GET | `/api/files/{sid}` · `/api/files/{sid}/{fid}` | list / download raw files |
| GET | `/api/history` | past runs |

## Tuning

- `server.py` → `RATES` — $/Mtoken rates for the live estimate.
- `server.py` → `SCAN_RULES` — add regexes for your own sensitive-data patterns.
- Coordinator model: `export COORDINATOR_MODEL=claude-opus-5` before `create_coordinator.py` for max quality.
