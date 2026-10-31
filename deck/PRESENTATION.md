# Wapsi: presentation guide

Deck: `deck/Wapsi_Final_Deck.pdf`. Rebuild with `deck/build_deck.swift`.

Check the real time limit first. The 3-minute demo is our plan, not a rule we were given.

## Before going on stage

1. `.env` on the demo laptop has `VOICE_MODE=bolna`, the Bolna keys and `DEMO_MERCHANT_PHONE`.
2. Click **Reset**. The board must show 21 handled, 9 visits, 2 approvals, 4 no action, 1 call.
3. The merchant phone is charged, on speaker, and not on silent.
4. The demo video is open in a tab, ready as the backup.
5. Open the app with `?demo` in the URL, like `http://localhost:5173/?demo=1`. A numbered strip
   gives one click to each demo step, and the left and right arrow keys move between steps.

## Opening (30 seconds, slides 1 and 2)

> 1.57 crore merchants pay for a Paytm device. When one goes quiet, nobody knows why. The box
> might be broken, the money might be stuck, or a rival might have offered ₹50 rent. So today
> it is a costly visit or nothing, and the merchant leaves.
>
> Wapsi is an AI teammate that finds out why, fixes what it can remotely, and sends a person
> only when one is truly needed.

## The insight (15 seconds, slide 4)

> Here is the idea that matters. If the box is offline but QR payments are still coming in,
> the device is broken, not the merchant gone. A rule-based alert cannot tell the difference.
> Wapsi can.

## Live demo (3 minutes)

| Time | Do | Say |
|---|---|---|
| 0:00 | Show the board | "37 merchants across India flagged this morning. And 25 shops in Guwahati dipped together, so Wapsi left them alone." |
| 0:20 | Open Karthik, Chennai | "Box offline, payments normal, signal healthy. So: device fault. The call did not fix it, so a rep goes with a replacement, and this brief." |
| 0:50 | Open Sunita, Almora, click Call | "A real call, in Hindi." Let it play. Stop talking. |
| 1:40 | Open Anirban, Kolkata | "Rent was charged twice. Wapsi refunded it and told him in Bengali." |
| 2:05 | Open Selvi, Coimbatore, then the manager view | "Wapsi tried a ₹405 refund. Our code blocked it: the limit is ₹150. So it asked the manager." Approve Balwinder's counter-offer. |
| 2:35 | Open results | "33 visits become 9, and more merchants come back. These outcomes are simulated from the assumptions shown here." |

If the call fails, do not debug on stage. Say "let me show you one we recorded" and play the video.

## Closing (20 seconds, slides 8 and 9)

> Paytm has already paid to win these merchants. Wapsi keeps them, at a fraction of the cost
> of a visit. We would prove it in one city with a control group, and scale only if it beats
> the cost of a field visit.

## Likely questions

**Is this real or scripted?**
The detector, Claude's reasoning, the guardrails and the phone call are real. The merchants and
Paytm's systems are simulated. The board opens from a real agent run saved in advance, because
37 cases take a few minutes. We can run a case live if you want to see it.

**How accurate is it?**
On our 37 simulated cases, the final version got every cause right and hit every target outcome.
That is data we generated ourselves, so it shows the method works, not real-world accuracy. A
pilot with a control group is how we would measure that.

**Where does the 25% come from?**
It is an assumption for sizing, not a result. It means 25% more than the control group, so
merchants who would have come back anyway do not count.

**5% going quiet a month sounds high.**
It is an illustrative assumption, and quiet is not the same as churned: most of it is broken
boxes and temporary problems. Paytm's own data would replace it on day one.

**What stops the AI from giving away money?**
Limits are in code, not in the prompt. The agent cannot refund more than ₹150 in total on a case,
so splitting a refund does not work. It cannot refund more than billing shows. Above the limit,
only the manager can approve.

**What about fraud? It is calling merchants about money.**
It never asks for OTPs, passwords or bank details. The code blocks those messages. Bank changes
happen only in the verified Paytm app.

**Can it call in other languages?**
Today's live call is Hindi. WhatsApp messages already go out in the merchant's language, and the
data covers 11 languages. Sarvam supports other Indian languages, so calls can follow.

**What does a call cost?**
Bolna's listed rate is about ₹5.50 a minute, so a 2-minute call is about ₹11 before telephony,
LLM and volume discounts. Quote the real cost from our test calls if we have it.

**Why these rent and visit figures?**
1.57 crore and 27 lakh come from Paytm's Q1 FY27 results. The rest come from public reports and
job postings, as listed on slide 2, so please correct us with internal numbers.

**Is step 5, Learn, built?**
Not yet. The control-group measurement is. Ranking which fixes work best comes next.

**Why not your stack on slide 6?**
Slide 6 is the production design. The prototype uses FastAPI, SQLite and Claude Sonnet, because
RabbitMQ and Celery add nothing to a one-day demo.

## Do not say

- "100% accurate", or any accuracy figure without "on simulated data"
- "Paytm already uses..." unless you have the source in hand
- Real merchant or real Paytm data: everything is simulated
