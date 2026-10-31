# Wapsi

An AI employee for Paytm's field sales team that wins back merchants who have gone quiet.

Team SLEEPINGFOXES (Ayush Tripathi, Aman Gupta). Paytm Build for India AI Hackathon, Track 3:
Autonomous AI Teammates.

[Pitch deck](deck/Wapsi_Final_Deck.pdf)

## The problem

Paytm finds out a merchant has left only when it is too late. 1.57 crore merchants pay for a Paytm
device, and when one goes quiet, nobody knows why. The only fix today is a costly field visit, and
a remote shop often gets nothing.

A device merchant earns Paytm about ₹3,000 a year, based on its Q1 FY27 payment and financial
services revenue. Wapsi spends about ₹12 on a call to protect that.

## What it does

Each morning, Wapsi compares every shop with its own normal and its local area, finds out why a shop
went quiet, and acts. A person steps in only when needed.

| Problem | The clue | What Wapsi does | When a person steps in |
|---|---|---|---|
| Device fault | Box offline, payments normal | Guides a restart, orders a replacement | Rep brings the new unit |
| SIM or network | Box offline, weak area signal | Refreshes the SIM, guides a restart in Hindi | If hardware must be swapped |
| Money problem | Settlements failing | Raises a ticket with evidence | Support clears the block |
| Billing anger | Duplicate rent, open complaint | Refunds the error, confirms in the merchant's language | Manager approves larger refunds |
| Competitor switch | Volume down, area normal | Prepares a counter-offer and a rep brief | Manager approves, rep visits |
| Closed or seasonal | Same dates last year | Stops chasing | Nobody |

If a whole area dips together, Wapsi does nothing.

Limits are enforced in code, not in the prompt: refund caps, contact caps, contact hours, opt-outs,
and no messages about OTPs or bank details. If Wapsi is unsure, a person decides.

## Built with

- **Agent:** Claude Sonnet with tool calling
- **Voice:** Bolna, Sarvam
- **Backend:** Python, FastAPI, SQLite
- **Frontend:** React, Vite

## What is real

| Real | Simulated |
|---|---|
| The detector | 500 merchants and all Paytm systems |
| Claude's reasoning and actions | Merchant replies, except on the live call |
| Limits and the audit log | WhatsApp, shown in a phone mockup |
| The Hindi phone call | Results, from the assumptions on the page |

The board opens from a saved run of the real agent. It diagnosed all 37 cases correctly, on data we
generated ourselves, so this shows the method works, not real-world accuracy.

The hosted demo uses that saved run and a scripted call.

## Run it

You need [uv](https://docs.astral.sh/uv/) and Node. No API keys are required.

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

Open <http://localhost:5173>. To run the real agent or make a real call, add your keys to `.env`.

## Test it

```
uv run python -m unittest discover -s tests -t .
```

`scripts/evaluate_agent.py` scores the real agent on all 37 cases, and uses API credit.
