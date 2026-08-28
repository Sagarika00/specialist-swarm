# RFP Response Studio

An AI bid desk built on the specialist-swarm starter. Drop in an RFP (paste or
upload a PDF/DOCX); a coordinator agent fans the work out to four specialist
sub-agents, synthesises a client-ready proposal, and runs the checks a real
services firm runs before a bid goes out — win/approval scoring, a proof-point
matrix against past engagements, a compliance gate, and a full audit trail.

Everything runs on the **Claude Managed Agents API** (multi-agent, research
preview) plus direct **Messages API** calls for the analysis features. No
database — session state is in memory, run history is a JSON file.

---

## What's in this repo

| Path | What it is |
| --- | --- |
| `setup_environment.py` | Creates the cloud Environment the agents run in → `.environment_id` |
| `create_specialists.py` | Creates the 4 specialist sub-agents → `.specialist_ids.json` |
| `upload_skills.py` | Packages `skills/*/SKILL.md`, uploads via Skills API, attaches each to its specialist |
| `create_coordinator.py` | Creates the coordinator with `multiagent: coordinator` and the specialist roster → `.coordinator_id` |
| `run_deal_desk.py` | CLI: runs the swarm against `synthetic-data/rfp-acme-corp.md`, streams events, saves the deliverable |
| `stretch_critic_subagent.py` | Optional 5th agent that reviews the draft before it ships |
| `skills/` | Domain knowledge: `pricing-playbook`, `legal-checklist`, `competitive-intel` |
| `synthetic-data/` | The trigger RFP, `past-wins.json`, `product-overview.md`, `past-engagements.json` |
| **`web/`** | **RFP Response Studio — the FastAPI backend + single-page UI** |

### `web/`

| File | Purpose |
| --- | --- |
| `server.py` | FastAPI app: swarm orchestration, SSE event stream, chat, instant read, win/approval scorecard, proof points, compliance scan, usage/cost, run history |
| `index.html` | The console — input, live swarm board, and the workspace tabs |
| `proposal.html` | The rendered proposal viewer (`/proposal/{sid}`) |
| `requirements.txt` | `fastapi`, `uvicorn`, `markdown`, `python-docx`, `pypdf`, `python-multipart`, `anthropic`, `python-dotenv` |

---

## The architecture

```
        RFP (paste / PDF / DOCX)
                │
                ▼
   Coordinator — "Senior Partner"  ── delegates in parallel ──┐
   (Claude Sonnet 5, multiagent: coordinator)                 │
        ┌───────────────┬───────────────┬────────────────┐    │
        ▼               ▼               ▼                ▼    │
   Pricing          Legal          Technical Fit     Competitive
   Specialist       Reviewer       Specialist        Intel Analyst
   Sonnet 5         Sonnet 5       Sonnet 5          Haiku 4.5
   +pricing-        +legal-                          +competitive-
    playbook         checklist                        intel
        └───────────────┴───────────────┴────────────────┘    │
                        │  verdicts flow back                 │
                        ▼                                     ▼
              Coordinator synthesises ──► proposal-response.md / .docx
                                          + INTERNAL_ brief (never sent)
```

Alongside the swarm, five **single-call Messages API** features answer questions
about the RFP without spinning up the whole team:

| Feature | Endpoint | Grounded in |
| --- | --- | --- |
| **Ask the RFP** (streaming chat) | `POST /api/chat/{sid}` | RFP + specialist verdicts + current draft |
| **Instant read** (bid triage) | `POST /api/brief/{sid}` | RFP only — customer, deal size, deadline, red flags, BID/NO-BID |
| **Win & approval scorecard** | `POST /api/scorecard/{sid}` | RFP + pricing playbook + past wins + track record (+ verdicts once the swarm has run) |
| **Proof-point matrix** | `POST /api/proofpoints/{sid}` | RFP + `past-engagements.json` |
| **Compliance scan** | `GET /api/scan/{sid}` | The generated deliverable (regex, no model) |

---

## Models used

| Component | Model | Why |
| --- | --- | --- |
| Coordinator | `claude-sonnet-5` | Fast + strong for orchestration and synthesis. Override with `COORDINATOR_MODEL=claude-opus-5` before `create_coordinator.py` for maximum quality. |
| Pricing / Legal / Technical Fit specialists | `claude-sonnet-5` | Domain reasoning over a skill + the RFP |
| Competitive Intel specialist | `claude-haiku-4-5-20251001` | Cheaper; a quick battlecard lookup |
| Chat, Instant read, Scorecard, Proof points | `claude-sonnet-5` (`web/server.py → CHAT_MODEL`) | Grounded Q&A and structured JSON extraction |
| Critic (stretch) | `claude-opus-5` | Adversarial review needs the sharpest model |

Beta header on every managed-agents call: `anthropic-beta: managed-agents-2026-04-01`.

---

## How the win / approval score works

`POST /api/scorecard/{sid}` is a hybrid — the model scores, Python does the maths:

1. One `claude-sonnet-5` call scores six factors **0–100** (with a one-line
   rationale each) from the RFP, the pricing playbook, past wins, and the
   delivery track record.
2. Python computes **win probability = Σ(score × weight)**. Weights live in
   `web/server.py → FACTOR_WEIGHTS`:

   | Factor | Weight |
   | --- | --- |
   | Solution fit | 25% |
   | Competitive position | 20% |
   | Commercial alignment | 20% |
   | Relationship & proof | 15% |
   | Risk & compliance | 10% |
   | Deadline feasibility | 10% |

3. The model separately estimates **internal approval probability** — the odds
   every required approver (VP Sales / Legal / Finance / …) signs off given the
   concessions the RFP forces — plus a `+`/`−` driver list.
4. It pulls the **segment historical win rate** from `past-wins.json`.

Both numbers are model estimates for decision support, not guarantees. The
factor weights are yours to tune.

Cost estimate rates ($/M tokens) are in `web/server.py → RATES`; the
API-reported figure from `session.usage` is shown alongside on completion.

---

## Run it

### One-time setup

```bash
cd specialist-swarm
cp .env.example .env          # then put your key in .env
python -m pip install -r requirements.txt -r web/requirements.txt

python setup_environment.py
python create_specialists.py
python upload_skills.py
python create_coordinator.py
```

Multi-agent is a research preview — your Console workspace may need to be
granted access.

### Start the studio

```bash
cd web
python -m uvicorn server:app --reload --port 8000
```

Open **http://localhost:8000**.

1. Paste an RFP **or** drag in a PDF / DOCX.
2. **Analyze & chat** — registers the RFP (no swarm cost) and unlocks all four
   workspace tabs.
3. **Instant read** → BID / NO-BID. **Win & approval** → the gauges.
   **Proof points** → the reference matrix. **Ask the RFP** → chat.
4. **Run the deal team** — Draft (markdown, ~5 min) or Final proposal
   (branded `.docx`, ~10 min). Watch the four specialists work in parallel.
5. **View proposal** (rendered in-browser), **Compliance scan**,
   **Usage & cost**, **History**.

### CLI (no UI)

```bash
python run_deal_desk.py          # streams events, saves to outputs/
python download_deliverable.py   # re-pull files from the last session
```

---

## Deliverables & the internal/external split

Every run produces two files:

- `proposal-response.md` / `.docx` — **client-facing**, what you send
- `INTERNAL_*.md` — walk-away positions, required sign-offs; **never sent**

The UI flags `INTERNAL_` files, withholds them from "download to send", and the
compliance scan looks for internal-only phrasing (walk-away prices, margins,
"do not send") leaking into the client deliverable.

---

## Re-theming for another domain

The orchestration is domain-agnostic. To turn this into contract review, vendor
security assessment, or M&A diligence, edit only:

- `SPECIALISTS` + prompts in `create_specialists.py`
- `COORDINATOR_SYSTEM` in `create_coordinator.py`
- 3 new `skills/<name>/SKILL.md` + `SKILL_TO_SPECIALIST` in `upload_skills.py`
- a new input document in `synthetic-data/`
- `synthetic-data/past-engagements.json` for the proof-point matcher

Then delete `.specialist_ids.json` / `.coordinator_id` and re-run setup steps
2–4. The `web/` UI needs no changes — the swarm board builds itself from the
event stream.

---

## Roadmap (shown in the "Deal lifecycle" tab)

Approval routing · capability-matrix export · clarification-question drafter ·
orals deck (pptx) · negotiation support · win/loss → memory.

---

## Notes

- This repo and any fork are **public**. `.env`, the `.*_id` files, `outputs/`
  and `web/.runs.json` are gitignored — keep it that way.
- No database. Restarting the server clears in-memory session state; run history
  persists in `web/.runs.json`.
