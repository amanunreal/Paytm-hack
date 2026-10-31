# Wapsi

An AI employee for Paytm's field sales team that wins back merchants who have gone quiet.

Built by Team SLEEPINGFOXES (Ayush Tripathi, Aman Gupta) for the Paytm Build for India AI
Hackathon, Track 3: Autonomous AI Teammates.

**Paytm finds out a merchant has left only when it is too late. Wapsi notices first, finds out
why, and fixes it.** It sends a person only when one is truly needed.

- Deck: [`deck/Wapsi_Final_Deck.pdf`](deck/Wapsi_Final_Deck.pdf)
- Demo script: [`deck/DEMO_SCRIPT.md`](deck/DEMO_SCRIPT.md)

## The problem

1.57 crore merchants pay for a Paytm device. When one goes quiet, nobody knows why. It could be a
dead box, stuck money, a billing error or a rival's offer. The only fix today is a costly field
visit, and a remote shop often gets nothing.

Every device merchant earns Paytm about ₹3,000 a year, not just ₹1,200 of rent. So Wapsi spends
about ₹12 on a call to protect ₹3,000 a year. ([How that is worked out](deck/PRESENTATION.md))

## What it does

| Problem | How Wapsi knows | What Wapsi does | When a human steps in |
|---|---|---|---|
| Device fault | Box offline, payments normal, signal healthy | Guides a restart, orders a replacement | Rep visits with the new unit |
| SIM or network | Box offline, weak signal in the shop and area | Refreshes the SIM, guides a restart by phone | Only if hardware must be swapped |
| Money problem | Settlements failing | Raises a ticket with evidence | Support clears the block |
| Billing anger | Duplicate rent, open complaint | Refunds a clear error, confirms in the merchant's language | Manager approves larger refunds |
| Competitor switch | Volume down, area normal | Prepares a counter-offer and a rep brief | Manager approves, rep visits |
| Closed or seasonal | All activity stopped, same dates last year | Stops chasing | Nobody |

A dip shared by a whole area is left alone on purpose.

The key insight: **box offline but QR payments still arriving means the device is broken, not the
merchant gone.**

## How it works

```
Merchant data -> Detector -> Claude agent (investigate, diagnose, act) -> Web app
                                  |                                         |
                        Guardrails in code                      Board, manager, results
                                  |
                  Hindi phone call (Bolna + Sarvam)
```

1. The **detector** compares each shop with its own normal and with its area.
2. The **agent** (Claude Sonnet) investigates with 8 read-only tools, records a diagnosis, and acts.
3. **Guardrails** run in code, not in the prompt: refund limits on the running total, contact caps,
   contact hours, opt-outs, and a block on messages about OTPs or bank details. If the agent is
   unsure, the case goes to a person.
4. Every action is logged, and the **web app** shows the reasoning, approvals and results.

| Part | Where |
|---|---|
| Simulator and planted cases | `wapsi/sim.py` |
| Detector | `wapsi/detector.py` |
| Agent, tools, actions, guardrails | `wapsi/agent.py`, `tools.py`, `actions.py`, `guardrails.py` |
| Live call | `wapsi/voice.py`, `scripts/bolna_agent.py` |
| API | `wapsi/api.py` |
| Web app | `web/` |

## What is real and what is simulated

| Real | Simulated |
|---|---|
| Detector | 500 merchants and all Paytm systems behind the tools |
| Claude's reasoning and tool calling | Merchant replies for cases not called live |
| Guardrails and the audit log | WhatsApp, shown in a phone mockup |
| Hindi phone call | Results outcomes, from the assumptions shown on the page |

The board opens from a real agent run saved in `wapsi/prerun.json`, which only saves if it passes
`scripts/evaluate_agent.py`. That run got all 37 cases right, on data we generated ourselves. It
shows the method works, not real-world accuracy. A pilot with a control group would measure that.

## Run it

You need [uv](https://docs.astral.sh/uv/) and Node.

```
cp .env.example .env
uv sync
uv run uvicorn wapsi.api:app --port 8000
```

In a second terminal:

```
cd web
npm ci
npm run dev
```

Open <http://localhost:5173>. Add `?demo=1` for the numbered demo path, where the arrow keys move
between steps.

The app works with no API keys: the board opens from the saved run, and `VOICE_MODE=mock` plays a
scripted call. For live runs, add `ANTHROPIC_API_KEY` to `.env`. For a real phone call, add the Bolna
keys and `DEMO_MERCHANT_PHONE`, and set `VOICE_MODE=bolna`.

## Hosted demo

`render.yaml` deploys the whole app as one free Render service. It runs with `WAPSI_PUBLIC=1` and no
API keys, so visitors see a saved real agent run and a scripted call, and cannot start paid runs or
real calls. The free tier sleeps when idle, so the first visit can take about a minute.

## Test it

```
uv run python -m unittest discover -s tests -t .   # free, no keys needed
uv run python scripts/evaluate_agent.py            # runs all 37 cases live, uses API credit
```

## Limits

- Only Hindi calls are live. WhatsApp messages go out in the merchant's language.
- The "Learn" step, ranking which fixes work best, is not built yet.
- The prototype uses FastAPI, SQLite and Claude Sonnet. Slide 6 shows the production design.
- ₹118 Cr and 4 lakh merchants on slide 8 are illustrations that assume 10% churn. Paytm does not
  publish device churn.
