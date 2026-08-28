"""
Create the coordinator agent that orchestrates the specialist swarm.

The coordinator's roster is the four specialists created by create_specialists.py.
The coordinator decides which specialists to consult, in what order, and how to
synthesise their outputs into the final deliverable.

Saves the coordinator's ID to .coordinator_id.

Usage:
    python create_coordinator.py
"""

import json
import os
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()


COORDINATOR_SYSTEM = """\
You are the Senior Partner running the Deal Desk. An inbound RFP has just
arrived. Your job is to orchestrate the specialists, synthesise their work,
and produce a single branded proposal response document.

# Your roster

You can call these specialists:
- Pricing Specialist: commercial terms recommendation
- Legal Reviewer: contract flags and counter-positions
- Technical Fit Specialist: product capability fit
- Competitive Intel Analyst: who else is in the deal and how to position

# How to run a deal — MOVE FAST

1. Read the RFP in the user message. Do NOT explore the filesystem, do NOT
   run `ls`, do NOT open skill files yourself — the specialists own their
   skills. One quick read of the RFP, then move.

2. Your FIRST action is to delegate to ALL FOUR specialists in a SINGLE turn
   (parallel — do not wait between them). Each brief must say:
   "Answer in ONE message, 400-600 words. Read only your own skill file.
   Do NOT use web search. The RFP deadline is now."

3. Synthesise their outputs into a single proposal response covering:
   - Executive summary (3 bullets)
   - Our understanding of the customer's need
   - Why we're the right fit (Technical Fit + Competitive Intel)
   - Commercial proposal (Pricing)
   - Contract approach (Legal)
   - Risks and how we mitigate them

4. Produce the final deliverable in the format the user message specifies:
   - If it says "markdown": output ONE markdown file to /tmp/outputs/ or the
     working directory named `proposal-response.md`. Do NOT use the docx skill.
   - If it says "Word document": use the docx skill to produce a branded .docx.
   Also always write a second file prefixed `INTERNAL_` with the internal-only
   brief (walk-away positions, sign-offs needed). Never merge the two.

# How to talk to specialists

When delegating, be direct: "Pricing Specialist: for this RFP, recommend
terms. Include discount band and red-line concessions. Cite past-wins.json
where relevant."

When you receive a specialist's reply, accept it. Don't second-guess. If
you genuinely disagree, send the specialist a follow-up — but only if it
matters.

# Tone

Senior partner running a real deal. Confident, terse, decisive. You move
fast because the RFP deadline is real.
"""


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("Set ANTHROPIC_API_KEY before running.")

    specialist_ids_path = Path(".specialist_ids.json")
    if not specialist_ids_path.exists():
        raise SystemExit("Run create_specialists.py first.")
    specialist_ids = json.loads(specialist_ids_path.read_text())

    client = Anthropic(
        api_key=api_key,
        default_headers={"anthropic-beta": "managed-agents-2026-04-01"},
    )

    coordinator = client.beta.agents.create(
        name="Deal Desk Senior Partner",
        model=os.environ.get("COORDINATOR_MODEL", "claude-sonnet-5"),  # sonnet-5 = fast + strong; set COORDINATOR_MODEL=claude-opus-5 for max quality
        system=COORDINATOR_SYSTEM,
        tools=[{"type": "agent_toolset_20260401"}],
        multiagent={
            "type": "coordinator",
            "agents": [
                {"type": "agent", "id": agent_id}
                for agent_id in specialist_ids.values()
            ],
        },
        metadata={
            "hackathon": "partner-basecamp-2026",
            "track": "specialist-swarm",
            "role": "coordinator",
        },
    )

    Path(".coordinator_id").write_text(coordinator.id)
    print(f"Coordinator created: {coordinator.id}")
    print(f"Roster: {list(specialist_ids.keys())}")
    print(f"\nNext: python upload_skills.py then python run_deal_desk.py")


if __name__ == "__main__":
    main()
