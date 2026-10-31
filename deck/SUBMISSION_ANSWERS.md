# Final submission form: answers

All 14 fields are required. Copy these in. Fill in the team lead's own details directly in the form.

## Details

| Field | Answer |
|---|---|
| City and Date | Bengaluru, 31st October |
| Track Selected | Track 3, Autonomous AI Teammates |
| Team Name | SLEEPINGFOXES |
| Team Lead Full Name | *Fill in on the form* |
| Team Lead Email Address | *Fill in on the form* |
| Phone Number | *Fill in on the form* |
| Project Title | Wapsi: an AI teammate that wins back merchants who have gone quiet |

## Provide a brief description of your project and the problem it solves

Paytm finds out a merchant has left only when it is too late. 1.57 crore merchants pay for a Paytm
device, and when one goes quiet, nobody knows why. It could be a dead box, stuck money, a billing
error or a rival's offer. The only fix today is a costly field visit, and a remote shop often gets
nothing.

Wapsi is an AI employee for Paytm's field sales team. Every morning it checks each merchant against
their own normal and their local area, finds the ones going quiet, investigates why, and acts. It
guides restarts by phone in Hindi, raises tickets with evidence, refunds clear billing errors,
prepares counter-offers, and books a rep with a ready brief only when a person is truly needed.
Refund limits and contact rules are enforced in code, and larger decisions go to the manager in one
tap. A key insight: if the box is offline but QR payments are still arriving, the device is broken,
not the merchant gone.

Why it matters: from Paytm's public Q1 FY27 results, a device merchant earns Paytm about ₹3,000 a
year, not just ₹1,200 of rent. So Wapsi spends about ₹12 on a call to protect ₹3,000 a year. Each
point of churn saved is 1.57 lakh merchants and about ₹47 crore a year. It also protects lending,
and it tells Paytm for the first time why merchants leave.

The prototype runs across 500 simulated merchants in 20 places and 11 languages. Its 37 flagged
cases were all diagnosed correctly in a saved real agent run, on data we generated ourselves.
Outcomes shown against the control group are simulated. A pilot would measure real impact.

## Technology Stack: databases, APIs, cloud etc.

- **Backend:** Python 3.12, FastAPI, Uvicorn
- **Database:** SQLite (the prototype), with PostgreSQL and Redis in the production design
- **Frontend:** React, Vite
- **Voice:** Bolna for the phone call, with Plivo telephony and Sarvam speech
- **APIs:** Anthropic Claude API, Bolna API
- **Cloud:** Render for the hosted demo
- **Production design:** RabbitMQ, Celery, Redis, PostgreSQL and the WhatsApp Cloud API (slide 6)

Paytm's systems and WhatsApp are simulated in the prototype.

## AI/ML tools, models or pre-trained models used (Claude Code, Copilot etc.)

**In the product**

- **Claude Sonnet 5.5** (`claude-sonnet-5-5`): the agent that investigates, diagnoses and acts, using
  tool calling
- **gpt-4.1-mini**, through Bolna: writes the short replies during the live phone call
- **Sarvam saaras:v4:** Hindi speech to text
- **Sarvam bulbul:v4-flash:** Hindi text to speech

The detector that flags merchants uses statistical rules, not a trained model.

**To build it**

- **Claude Code:** used by both team members to write and test the code, the deck and the documents

## Links and upload

| Field | Answer |
|---|---|
| Working Demo URL | *Add after deploying to Render* |
| Working Demo Video Recording URL | *Add after recording. Set to "anyone with the link can view"* |
| GitHub/Code Repository URL | https://github.com/amanunreal/Paytm-hack |
| Upload your Pitch Deck | `deck/Wapsi_Final_Deck.pdf` |
