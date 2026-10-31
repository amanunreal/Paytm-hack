"""Limits the agent cannot talk its way past. These run in code, not in the prompt."""
import os
import re

WAIVER_LIMIT = 150  # Rupees the agent may refund alone. Anything larger goes to the manager.
MAX_CONTACTS_PER_WEEK = 3  # Calls and WhatsApp messages combined, per merchant.
CONTACT_HOURS = (8, 21)  # Local time. Never contact merchants outside these hours.
DEMO_HOUR = 8  # The board opens at 8:00 AM.
COUNTER_OFFER_MIN_GMV = 575000  # Monthly rupees before a shop qualifies for a counter-offer.

# Agent messages must never ask for these. Verified flows handle them instead.
SENSITIVE = re.compile(r"\b(otp|cvv|pin|password|ifsc|account number)\b|ओटीपी|पासवर्ड|আইএফএসসি", re.IGNORECASE)


class Blocked(Exception):
    """A guardrail stopped this action. The message goes back to the agent."""


def current_hour():
    """The simulated morning, not the laptop's clock, so an evening demo still runs."""
    return int(os.environ.get("WAPSI_CLOCK_HOUR", DEMO_HOUR))


def check_contact(conn, merchant_id):
    merchant = conn.execute("SELECT opted_out FROM merchants WHERE id = ?", (merchant_id,)).fetchone()
    if merchant["opted_out"]:
        raise Blocked("This merchant has opted out of contact. Do not call or message them.")
    start, end = CONTACT_HOURS
    if not start <= current_hour() < end:
        raise Blocked(f"Merchants may only be contacted between {start}:00 and {end}:00.")
    used = conn.execute("SELECT COUNT(*) FROM contacts WHERE merchant_id = ?", (merchant_id,)).fetchone()[0]
    if used >= MAX_CONTACTS_PER_WEEK:
        raise Blocked(f"This merchant already had {used} contacts this week, which is the limit.")


def check_waiver(amount, already_refunded=0):
    """The limit covers the running total, so splitting a refund cannot get around it."""
    if amount + already_refunded > WAIVER_LIMIT:
        raise Blocked(
            f"Rs {amount + already_refunded} is over your Rs {WAIVER_LIMIT} waiver limit. "
            "Use request_approval so the manager can decide."
        )


def check_message(text):
    if SENSITIVE.search(text):
        raise Blocked("Never ask for or mention OTPs, passwords or bank details in a message.")


def check_counter_offer(monthly_gmv):
    if monthly_gmv < COUNTER_OFFER_MIN_GMV:
        raise Blocked(
            f"This shop's monthly volume of Rs {monthly_gmv} is below the Rs {COUNTER_OFFER_MIN_GMV} "
            "counter-offer bar. Use book_visit with a brief so a rep can talk to them instead."
        )
