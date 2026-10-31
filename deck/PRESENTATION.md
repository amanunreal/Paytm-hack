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

## How to explain it

Mentor feedback: the idea is good, but we did not explain it well or show why it would change
the business. So tell one shopkeeper's story, then give three business reasons. Say "AI employee"
and "shopkeeper". Avoid tool names, "agent loop" and "guardrails" until someone asks.

**The whole idea in one line:** Paytm finds out a merchant has left only when it is too late.
Wapsi is an AI employee who notices first, finds out why, and fixes it.

## Opening (45 seconds, slides 1 and 2)

> Meet a kirana owner in Chennai. His Paytm box died three days ago. Customers still pay him by
> QR, so money comes in, but the box is silent and he is still paying rent. A rival has offered
> him a box for ₹50. Paytm does not know any of this. Nobody calls him. Next month, he is gone.
>
> Now multiply him across 1.57 crore merchants. Today the only fix is a costly field visit, and
> a remote shop often gets nothing.
>
> Wapsi is an AI employee for the field sales team. Every morning it checks every merchant,
> finds the ones going quiet, works out why, and fixes what it can. It sends a person only when
> one is truly needed.

## The insight (15 seconds, slide 4)

> Here is the clever part. Box offline, but QR payments still coming in? The device is broken,
> not the merchant gone. A rule-based alert cannot tell the difference. Wapsi can.

## Live demo (3 minutes)

| Time | Do | Say |
|---|---|---|
| 0:00 | Show the board | "37 merchants across India flagged this morning. And 25 shops in Guwahati dipped together, so Wapsi left them alone." |
| 0:20 | Open Karthik, Chennai | "Box offline, payments normal, signal healthy. So: device fault. The call did not fix it, so a rep goes with a replacement, and this brief." |
| 0:50 | Open Sunita, Almora, click Call | "A real call, in Hindi." Let it play. Stop talking. |
| 1:40 | Open Anirban, Kolkata | "Rent was charged twice. Wapsi refunded it and told him in Bengali." |
| 2:05 | Open Selvi, Coimbatore, then the manager view | "Wapsi tried a ₹405 refund. Our code blocked it: the limit is ₹150. So it asked the manager." Approve Balwinder's counter-offer. |
| 2:35 | Open results | "33 visits become 9, and 15 more merchants come back. These outcomes are simulated from the assumptions shown here." |

If the call fails, do not debug on stage. Say "let me show you one we recorded" and play the video.

## Why this changes the business (45 seconds, slide 8)

Say this after the demo. This is the part the mentor wants judges to remember.

> Everyone thinks a merchant is worth ₹1,200 of rent. Paytm's own results say about ₹3,000 a
> year. So we spend ₹12 on a call to protect ₹3,000 a year.
>
> Three reasons this is a game changer.
>
> **One: growth Paytm does not have to buy.** Every merchant kept is one you never win twice.
> Each point of churn saved is 1.57 lakh merchants and about ₹47 crore a year, and it stacks.
>
> **Two: it protects lending.** Financial services is growing 45%, and the shops that take loans
> are device merchants. A shop that goes quiet stops being a loan customer.
>
> **Three: for the first time, Paytm knows why merchants leave.** Every case gets a reason. A
> billing bug, a bad network area, a rival in one city. You can fix the cause, not just the
> merchant. No human team can do that across 1.57 crore shops.
>
> Paytm's AI helps win merchants. Wapsi keeps them. Let us prove it in one city with a control
> group, and scale only if it beats the cost of a field visit.

## Likely questions

**Is this real or scripted?**
The detector, Claude's reasoning, the guardrails and the phone call are real. The merchants and
Paytm's systems are simulated. The board opens from a real agent run saved in advance, because
37 cases take a few minutes. We can run a case live if you want to see it.

**How accurate is it?**
On our 37 simulated cases, the final version got every cause right and hit every target outcome.
That is data we generated ourselves, so it shows the method works, not real-world accuracy. A
pilot with a control group is how we would measure that.

**Where does ₹3,000 come from?**
Paytm's Q1 FY27 net payment revenue (₹601 Cr) plus financial services revenue (₹814 Cr), times
four, divided by 1.57 crore devices. That is about ₹3,600, and we round down. It is an average
that includes non-device merchants, so a small shop may be worth less.

**Is 10% churn real? Where do 4 lakh and ₹118 Cr come from?**
Paytm does not publish device churn, so 10% a year and saving 1 in 4 are our assumptions.
1.57 Cr x 10% x 25% is about 4 lakh merchants, at ₹3,000 each. That is why we use "each point of
churn saved is about ₹47 crore": it holds whatever the real churn is. Paytm can use its own number.

**₹118 crore is only about 1% of revenue. Why is that a game changer?**
It is the first year only. Merchants kept stay, so it stacks, and it costs no new device or
acquisition. At Paytm's 55% contribution margin it is about ₹65 crore a year. Then add the loans
protected and the root causes found. The bigger prize is knowing why merchants leave.

**Could a bigger support team do this?**
Not at this scale, in 11 languages, every morning. A person also cannot compare each shop with
its own history and its neighbours across 1.57 crore merchants.

**Why would Paytm not build this itself?**
They could, and that is the point of the pilot. Their AI work has focused on winning merchants
and helping them run a business. This owns retention, and it uses data they already have.

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
- "₹118 crore" without "if churn is 10%": it is an illustration, not a forecast
- "85% of loans go to device merchants" unless you have checked the source: Paytm said it in
  late 2025, and I could only see it in a search summary
