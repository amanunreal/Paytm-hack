# Wapsi: team plan

The single source of truth for A1 and A2. If it is not in here, it is not agreed.
Pitch deck: `Wapsi_Track3_Pitch.pdf`. Judging criteria: shortlist email.

## What we are building

A web app where an AI teammate handles Paytm device merchants who have gone quiet.
It finds out why, fixes what it can remotely, books a rep only when needed, asks a
manager for bigger decisions, and shows its impact against a control group.

**The one sentence to land:** box offline but QR payments still arriving means the
device is broken, not the merchant gone.

## The demo (3 minutes, one browser tab plus one phone)

| # | What the audience sees | Screen |
|---|---|---|
| 1 | 8:00 AM all-India board: 37 flagged across states, sorted by cause. Banner: 25 Guwahati merchants dipped with their area, so Wapsi did nothing | Ops board |
| 2 | Open device fault case M0044 (Karthik Nadar, kirana, Chennai): box offline, QR still at normal volume, diagnosis, rep brief | Case detail |
| 3 | Click "Call" on M0418 (Sunita Maurya, tailor, Almora, SIM problem): a real phone rings, Hindi conversation on speaker, the board turns green | Ops board + phone |
| 4 | Billing case M0285 (Anirban Ghosh, Kolkata): rent reversed, WhatsApp confirmation in Bengali appears in the phone mockup | Case detail |
| 5 | Over-limit waiver blocked by guardrail, then manager approves counter-offer M0393 (Balwinder Gill, Ludhiana) in one tap | Manager view |
| 6 | AI group vs control: visits saved, cost, Rs recovered. Say out loud that these are simulated | Results |

**All-India by design.** The prototype covers 20 places, from metros to remote towns, in
11 languages. Each case carries `state` and `language`, and the agent replies in the
merchant's language. A shop is still compared with its own area, because a national
average would hide a local dip. The live call is Hindi. Slide 9's one-city pilot is only
the rollout plan, not a limit on the product.

## Real vs simulated

Say this honestly if asked.

| Real | Simulated |
|---|---|
| Detector | 500 merchants and all Paytm systems behind the tools |
| Agent reasoning and tool calling (Claude) | Merchant replies for the 36 cases not called live |
| Guardrails, enforced in code | WhatsApp, shown in a phone mockup on the page |
| Audit log | Device restart, tickets, waivers, visits (they write to our DB) |
| Live Hindi phone call (Bolna) | Results outcomes, from the assumptions shown on the page |
| | Merchants' locations and languages: realistic, but invented |

## Target numbers

The AI cohort must reach this on the board. Test: `tests/test_api.py`.

| Cause | Total | Handled remotely | Rep visit | Needs approval | No action |
|---|---|---|---|---|---|
| device_fault | 7 | 2 | 5 | | |
| sim_network | 10 | 8 | 2 | | |
| money_problem | 6 | 6 | | | |
| billing_anger | 7 | 6 | | 1 | |
| competitor_switch | 3 | | 2 | 1 | |
| closed_seasonal | 4 | | | | 4 |
| **Total: 37** | | **22** | **9** | **2** | **4** |

M0418 stays open until the live call, so the board shows 21 handled until then.

## Who owns what

Stay inside your own files and merge conflicts will not happen. To change anything
in **Shared**, tell the other person first.

### A1: the brain

- `wapsi/agent.py` and `wapsi/tools.py` (to create): replace `wapsi/stub_agent.py`
- Guardrails: waiver limits, contact caps, night calls, escalate when unsure
- `wapsi/sim.py`, `wapsi/detector.py`, `wapsi/results.py`
- Fixes to the deck and the final presentation

### A2: everything people see and hear

- `web/` (to create): Vite + React. Ops board, case detail with trace, phone mockup,
  manager view, results
- `wapsi/voice.py`: Bolna call, poll for the transcript, hand back the outcome
- Recording the demo video

### Shared (agree first)

- `wapsi/api.py`, `wapsi/store.py`, this file, `.env.example`

## The contract

Base URL `http://localhost:8000`. Interactive docs at `/docs`. Run the Vite dev server
with a proxy from `/api` to port 8000.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/board` | Headline counts, area dips, AI cohort cases with `state` and `language` |
| GET | `/api/cases/{id}` | Case, merchant, 14 days of signals, events, approvals |
| GET | `/api/events?after=N` | New events after id N. Poll every second |
| POST | `/api/run` | Run the agent on every new AI case (background) |
| POST | `/api/cases/{id}/run` | Run one case live |
| POST | `/api/cases/{id}/call` | Start the call (background) |
| GET | `/api/approvals` | Pending approvals |
| POST | `/api/approvals/{id}/decide` | Body `{"decision": "approve" \| "reject"}` |
| GET | `/api/results` | AI vs control, with `simulated: true` and the assumptions |
| POST | `/api/reset` | Back to the 8:00 AM state. Use between demo takes |

Live updates are polling, not websockets: it is simpler and cannot die on stage.

**Fixed values** (the UI may rely on these)

- `status`: `new`, `working`, `awaiting_call`, `on_call`, `awaiting_approval`, `done`, `control`
- `bucket`: `handled_remote`, `rep_visit`, `needs_approval`, `no_action`, or `null`
- `cause`: the six rows in Target numbers, or `null`
- event `kind`: `thought`, `tool_call`, `tool_result`, `guardrail`, `call`, `whatsapp`,
  `approval`, `status`

`agent_mode` in `/api/board` is `stub` until A1's agent lands. Show it as a visible badge,
so nobody demos canned reasoning by accident. A1 changes it to `live`.

A1 and A2 never call each other's code directly. Both only read and write through
`wapsi/store.py`, so the agent can be swapped without touching the UI.

## Rules that protect the score

- The agent must never read `ground_truth`.
- Waiver limits live in the tool, never only in the prompt.
- No bank or IFSC details over voice. Send the merchant to a verified flow instead.
- `/api/reset` must always return to a clean demo.
- Pre-run the 36 background cases. Only the hero moments happen live.

## Checkpoints

Stop, pull, run the whole demo together, and update Status below.

| CP | Done when |
|---|---|
| 1 | A2 sees the stub board in the browser. A1 has real Claude output for one case. One Hindi call rings a phone |
| 2 | Real agent gets all 37 causes right. Board, case detail and call work end to end |
| 3 | The full demo runs twice in a row from `/api/reset`. **Feature freeze** |
| 4 | Demo video recorded (it is also the backup), deck fixed, everything submitted |

If time runs short, cut in this order: learning ranking, then rep view (show the brief
in case detail). Never cut the trace, live call, guardrail block or results.

## Running it

```
git clone git@github.com:amanunreal/Paytm-hack.git
cp .env.example .env                      # then fill in your keys
uv sync                                   # first time
uv run uvicorn wapsi.api:app --reload     # API on port 8000
uv run python -m unittest discover -s tests -t .
```

Keys go in `.env`, which is git-ignored. Never paste keys in chat.

Work on `main` in small commits. Run `git pull --rebase` before every push, and push
at least at every checkpoint. No co-author lines in commit messages.

## Staying in sync

Talk to each other for decisions. Use this file and git for the record. Before starting
a task, set it to `doing` and push: that push is what stops both of you doing the same
work. `CLAUDE.md` gives both Claudes the same rules.

## Tasks

State is `todo`, `doing` or `done`. Keep each task on its own line.

| ID | Task | Owner | State |
|---|---|---|---|
| T1 | Simulator, detector, API contract with stub agent | A1 | done |
| T2 | Real agent loop with read-only tools, working on one case | A1 | todo |
| T3 | Action tools and guardrails, including the waiver block | A1 | todo |
| T4 | Real agent gets all 37 causes right, stub deleted, `agent_mode` set to `live` | A1 | todo |
| T5 | Deck fixes and final presentation | A1 | todo |
| T6 | Vite + React app showing the ops board from `/api/board` | A2 | done |
| T7 | Case detail with live agent trace | A2 | todo |
| T8 | Bolna agent with Sarvam voice: one Hindi call rings a phone | A2 | todo |
| T9 | `wapsi/voice.py`: real call, poll transcript, finish the case | A2 | todo |
| T10 | Phone mockup and manager approval view | A2 | todo |
| T11 | Results page showing the simulated label and assumptions | A2 | todo |
| T12 | Record the demo video | A2 | todo |

## Decisions

- Whole demo is in the browser. The call rings a real phone, started from the page.
- Voice is Bolna for the call, with Sarvam for Hindi speech. $5 free credit to start.
- WhatsApp is a phone mockup on the page, labelled simulated if asked.
- SQLite for today. Slide 6 is the production design.
- The demo agent runs on Claude Sonnet (`claude-sonnet-5-5`), set by `WAPSI_MODEL`.
- All-India data: 20 places, 11 languages, compared with their local area.
