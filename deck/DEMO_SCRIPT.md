# Wapsi: two-person demo script

## Who does what

| | A1 (Aman) | A2 (Ayush) |
|---|---|---|
| **Job** | The story and the business case | The product and the screen |
| **Speaks** | Opening, why it matters, closing | The live walkthrough |
| **Hands** | Holds the phone and plays the merchant | Drives the laptop: every click and slide change |
| **In Q&A** | Business, numbers, rollout | How it works, tech, guardrails |

Rules for both:

- One person talks at a time. Hand over by name: "Ayush, show them."
- Whoever is not talking looks at the screen, not at their notes.
- Go slowly. If you lose your place, the next demo step on the strip is your prompt.
- Say "shopkeeper" and "AI employee". Avoid "agent loop", tool names and "guardrails" unless asked.

## Before you start

**A1**

- `DEMO_MERCHANT_PHONE` is your number. Phone charged, ringer on, ready to go on speaker.
- Practise the Hindi replies in Part 3.

**A2**

- `VOICE_MODE=bolna` in `.env`, and the API and web app restarted on the latest code.
- Deck open in full screen, on slide 1.
- App open at `http://localhost:5173/?demo=1`. Click **Reset**, then check the board shows 21 / 9 / 2 / 1 / 4.
- Demo video ready in another tab as the backup.
- Left and right arrow keys move through the 7 demo steps.

## Part 1: The story

**Screen: slide 1, then slide 2**

**A1:** Hi, I'm Aman, this is Ayush, from team SleepingFoxes. Let me start with one shopkeeper.

A kirana owner in Chennai. His Paytm box died three days ago. Customers still pay him by QR, so
money is coming in, but the box is silent, and he is still paying rent. A rival has offered him
a box for fifty rupees. Paytm does not know any of this. Nobody calls him. Next month, he is gone.

*A2 moves to slide 2.*

**A2:** Now multiply him across 1.57 crore merchants who pay for a Paytm device. When one goes
quiet, nobody knows why. The only fix today is a costly field visit, and a remote shop often
gets nothing.

**A1:** So we built Wapsi. It's an AI employee for Paytm's field sales team. It notices a shop
going quiet, finds out why, and fixes what it can. It sends a person only when one is truly
needed. Ayush, show them its morning.

## Part 2: The board

**Screen: app, step 1, Board**

**A2:** It's 8 AM. Wapsi has watched 500 simulated merchants across India, in 11 languages, and
flagged 37. Most are already handled. People only see what truly needs them.

*Point at the Guwahati banner.*

**A2:** And look at this. 25 shops in Guwahati dipped together. That's the whole area, not a
merchant problem, so Wapsi did nothing. Knowing when not to act matters too.

## Part 3: Three problems, three different fixes

### Step 2: Device fault

**Screen: Karthik Nadar, Chennai** *(right arrow)*

**A2:** This is the shopkeeper from our story. His box has been offline for three days, but QR
payments are at 105% of normal.

**A1:** This is the clever part. Box offline, but payments coming in? The device is broken, not
the merchant gone. A simple alert can't tell the difference. Wapsi can.

**A2:** It tried a guided restart. That failed, so it booked a rep, with this brief: carry a
new box, restart already tried. The rep walks in prepared.

### Step 3: Live call

**Screen: Sunita Maurya, Almora** *(right arrow)*

**A2:** Sunita's shop is in Almora, where the network is weak. Wapsi thinks a phone call can fix
this, so it is calling her. This is a real call, in Hindi. Aman will play Sunita.

*A2 clicks **Call**. A1's phone rings. A1 answers on speaker and holds it up to the room.*
*Neither of you speaks over the call. Wait for Wapsi to finish each sentence.*

| Wapsi says | A1 replies |
|---|---|
| Greets you, says it is calling from Paytm | "Haan ji, boliye." |
| Says your money is safe, asks if the box has no sound | "Haan, teen din se awaaz nahi aa rahi." |
| Asks you to switch the box off, wait 10 seconds, switch it on | "Theek hai." *Wait 3 seconds.* "Kar diya." |
| Asks if the light is on and the box is working | "Haan, batti jal gayi. Box chalu ho gaya." |
| Says thank you and ends the call | "Dhanyavaad." |

*The call ends. The page takes a few seconds to read the conversation.*

**A2:** It's reading the call now, and when it finishes, the case closes by itself.

*Once the case shows **Handled remotely**:*

**A2:** Fixed, with no visit, no human, in the shopkeeper's language. That's 22 handled now.

### Step 4: Billing fix

**Screen: Anirban Ghosh, Kolkata** *(right arrow)*

**A1:** Now billing, which is where merchants get angry.

**A2:** Anirban was charged rent twice. Wapsi found it, refunded the 80 rupees, and told him on
WhatsApp in Bengali. This message is simulated, but the words are the AI's own.

## Part 4: Keeping a human in control

### Step 5: Waiver blocked

**Screen: Selvi Nadar, Coimbatore** *(right arrow)*

**A1:** You're probably thinking: should an AI be allowed to give away money?

**A2:** Selvi was overcharged 405 rupees. Wapsi tried to refund it, and this red box is our code
stopping it. Its limit is 150 rupees. That limit is in the system, so it can't talk its way
past it.

**A1:** So it did what a good employee does. It asked the manager.

### Step 6: Manager

**Screen: Manager** *(right arrow)*

**A2:** This is the manager's morning: two decisions, one tap each. Balwinder in Ludhiana looks
like he's moving to a rival, so Wapsi proposed 50 rupees rent. Approve, and a rep visits with
the offer.

*A2 clicks **Approve** on Balwinder.*

### Step 7: Results

**Screen: Results** *(right arrow)*

**A1:** Did it work? We compare against a control group: the same mix of merchants, without
Wapsi. 33 visits become 9, and about 15 more merchants come back. To be straight with you,
these outcomes are simulated from the assumptions on this page. A real pilot would measure them.

## Part 5: Why this changes the business

**Screen: slide 8** *(A2 switches back to the deck)*

**A1:** Everyone thinks a merchant is worth 1,200 rupees of rent. Paytm's own results say about
3,000 rupees a year. So we spend 12 rupees on a call to protect 3,000 a year.

Three reasons this is a game changer. One: it's growth Paytm doesn't have to buy. Every merchant
kept is one you never win twice. Each point of churn saved is 1.57 lakh merchants, and about 47
crore rupees a year.

**A2:** Two: it protects lending. Financial services is growing 45%. A shop that goes quiet stops
being a loan customer.

**A1:** And three, the big one: for the first time, Paytm knows why merchants leave. Every case
gets a reason. A billing bug, a bad network area, a rival in one city. You fix the cause, not
just the merchant. No human team can do that across 1.57 crore shops.

*A2 moves to slide 9.*

**A2:** We'd prove it the right way: one city, with a control group. It scales only if it beats
the cost of a field visit.

*A2 moves to slide 10.*

**A1:** Paytm works hard to win every merchant. Wapsi keeps them. Thank you.

## If something goes wrong

| What happens | Who acts | What to do |
|---|---|---|
| Phone doesn't ring in 15 seconds | A2 | Say "the network here has its own opinions". Click **Call again** once when it appears |
| Call fails twice | A2 | Say "here's one we recorded" and play the video. Do not debug on stage |
| The call won't end, or runs past 60 seconds | A1 | Say "Dhanyavaad", and carry on |
| Case doesn't close after 20 seconds | A2 | Say "it finishes reading in a moment" and move on. Do not wait |
| Wapsi says the box isn't fixed | A2 | Say "and that's the other path: a rep gets booked automatically" |
| A page won't load | A2 | Refresh once, then use the video |
| Someone loses their words | The other person | Pick up from the next line |

## If you get less time

Measured at a calm 135 words a minute, plus about 60 seconds for the call and 45 seconds of
clicks and pauses. Rehearse with a stopwatch, because the call is the part most likely to vary.

| Version | What to do | Length |
|---|---|---|
| **Full** | Everything above | About 7 minutes |
| **Short** | Cut Step 4, Step 6, A2's reason two, the slide 9 line, A2's "multiply him" paragraph and the rep brief line in Step 2. On Step 5, A1 adds: "and the manager approves it in one tap" | About 5½ minutes |
| **Shortest** | Keep only A1's story and "So we built Wapsi", the first board paragraph, Step 2's insight, the live call, "12 rupees to protect 3,000", reason three, and "Thank you" | About 3½ minutes |

Never cut the live call or the line "12 rupees to protect 3,000". If you have a strict 3 minutes,
use the Shortest version and play the recorded call instead of ringing the phone live.

## Questions

Answer as your role, then stop. Don't both answer. Full answers are in `deck/PRESENTATION.md`.

| Question about | Who answers |
|---|---|
| Is it real, how accurate, how it works, safety, fraud, stack | **A2** |
| ₹3,000, churn, ₹118 Cr, why Paytm needs it, rollout, cost | **A1** |
| Anything you don't know | Say "we don't know that yet, a pilot would tell us" |
