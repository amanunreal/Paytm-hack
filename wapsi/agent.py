"""The real agent: Claude investigates one quiet merchant and acts on what it finds.

Try one case with `uv run python -m wapsi.agent C-M0044`.
"""
import json
import os
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from wapsi import guardrails, store
from wapsi.actions import CaseActions
from wapsi.tools import ACTION_TOOLS, READ_TOOLS, CaseTools

MAX_TURNS = 16
DEFAULT_MODEL = "claude-sonnet-5-5"

SYSTEM = f"""You are Wapsi, a Merchant Retention Associate for Paytm's field sales team in India. \
You find out why a shop using a Paytm device has gone quiet, fix what you can remotely, and send a \
person only when one is truly needed.

A shop gets flagged when its payments fall well below its own normal, or when its device stops \
reporting. Check the evidence before concluding. Your tools describe only this merchant and their \
area, and QR payments can keep arriving when the device itself is offline.

Investigate first, then call record_diagnosis once with one of these causes:
- device_fault: the device has failed, but the shop is trading normally and signal history is healthy.
- sim_network: the device is offline because of poor connectivity, shown by weak signal or \
  dropouts in the shop's history and area.
- money_problem: settlements are failing, for example a bank or KYC issue.
- billing_anger: the merchant is upset about a charge, such as rent deducted twice.
- competitor_switch: Paytm volume has fallen while nearby shops are normal and nothing is wrong \
  with the device, settlements or billing.
- closed_seasonal: the shop has stopped entirely, and did the same around these dates last year.
- unclear: the evidence does not support one cause. Do not act; a human will look.

Then act, always trying the cheapest fix likely to work. A visit is costly, so use one only when \
remote options have failed or a relationship is needed:
- device_fault: call to guide a power cycle. If the device stays offline, order a replacement and \
  book a visit.
- sim_network: refresh the SIM session, then call to guide a power cycle. If the device stays \
  offline, order a replacement and book a visit.
- money_problem: create a ticket with the evidence, then send a WhatsApp telling the merchant the \
  team is on it and that any changes to bank details happen only in their Paytm app.
- billing_anger: refund the duplicate charges with offer_waiver and confirm by WhatsApp. If the \
  total is over your Rs {guardrails.WAIVER_LIMIT} limit, use request_approval instead, and do not \
  split it into smaller refunds.
- competitor_switch: request_approval for a counter-offer of Rs 50 monthly rent with a rep brief. \
  If the shop does not qualify, book a visit with a brief.
- closed_seasonal: do not contact the merchant. Close the case as no_action.

Write every WhatsApp message in the merchant's language and script, in simple words. Never ask \
for or name OTPs, PINs, passwords, IFSC codes or account numbers in a message, even to explain a \
problem: say "bank details" instead. If a tool blocks an action, follow what it says and do not \
try to get around it. Report only what the tools show.

Finish by calling close_case."""


def as_text(result):
    return json.dumps(result, default=str, ensure_ascii=False)


def error_result(block, message):
    return {"type": "tool_result", "tool_use_id": block.id, "is_error": True, "content": message}


def run_tool(conn, case_id, tools, actions, block):
    """Run one tool call and return its tool_result. Failures go back to the model."""
    store.add_event(conn, case_id, "tool_call", block.name, block.input or None)
    action_names = {tool["name"] for tool in ACTION_TOOLS}
    read_names = {tool["name"] for tool in READ_TOOLS}
    if block.name not in action_names | read_names:
        return error_result(block, f"Unknown tool {block.name}. Available: {sorted(action_names | read_names)}")
    try:
        if block.name in action_names:
            result = getattr(actions, block.name)(**block.input)
        else:
            result = getattr(tools, block.name)()
    except guardrails.Blocked as blocked:
        store.add_event(conn, case_id, "guardrail", f"Blocked: {block.name}", {"text": str(blocked)})
        return error_result(block, str(blocked))
    store.add_event(conn, case_id, "tool_result", block.name, result)
    return {"type": "tool_result", "tool_use_id": block.id, "content": as_text(result)}


def hand_to_human(conn, case_id, reason):
    """Unsure means a person decides, never a guess. A visit is the safe default."""
    store.add_approval(conn, case_id, "review", 0, reason, "rep_visit")
    store.update_case(conn, case_id, status="awaiting_approval", summary=reason)
    store.add_event(conn, case_id, "status", "Handed to a human", {"text": reason})


def create_message(client, messages):
    return client.beta.messages.create(
        model=os.environ.get("WAPSI_MODEL", DEFAULT_MODEL),
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        thinking={"type": "adaptive", "display": "summarized"},
        output_config={"effort": "medium"},
        system=SYSTEM,
        tools=[*READ_TOOLS, *ACTION_TOOLS],
        messages=messages,
    )


def run_case(conn, case_id, client=None):
    """Work one case until the agent closes it, or a person has to take over."""
    client = client or anthropic.Anthropic()
    case = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    if case["cohort"] != "ai":
        raise ValueError(f"{case_id} is in the control group, so the agent must leave it alone")
    tools = CaseTools(conn, case["merchant_id"])
    actions = CaseActions(conn, case_id, case["merchant_id"])
    store.update_case(conn, case_id, status="working")
    messages = [{"role": "user", "content": (
        f"Case {case_id}: merchant {case['merchant_id']} was flagged this morning. Recent payment volume "
        f"is {case['volume_ratio']:.0%} of normal, and the device has been offline on "
        f"{case['offline_days']} of the last 3 days. Work this case."
    )}]

    for _ in range(MAX_TURNS):
        response = create_message(client, messages)
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason == "refusal":
            hand_to_human(conn, case_id, "The agent declined this case, so a person should review it.")
            return

        results = []
        for block in response.content:
            if block.type == "thinking" and block.thinking:
                store.add_event(conn, case_id, "thought", block.thinking)
            elif block.type == "text" and block.text:
                store.add_event(conn, case_id, "thought", block.text)
            elif block.type == "tool_use":
                results.append(run_tool(conn, case_id, tools, actions, block))

        if actions.closed:
            return
        if not results:
            messages.append({"role": "user", "content": "Finish this case by calling close_case."})
            continue
        messages.append({"role": "user", "content": results})

    hand_to_human(conn, case_id, "The agent could not finish this case, so a person should review it.")


if __name__ == "__main__":
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    store.ensure_db(keep_cases=True)
    with store.connect() as connection:
        run_case(connection, sys.argv[1])
        case_row = dict(connection.execute("SELECT * FROM cases WHERE id = ?", (sys.argv[1],)).fetchone())
        for event in store.event_rows(connection.execute(
            "SELECT * FROM events WHERE case_id = ? ORDER BY id", (sys.argv[1],)
        )):
            if event["kind"] not in ("tool_result", "thought"):
                print(f"[{event['kind']}] {event['title'][:120]} {as_text(event['detail'])[:220]}")
    print(as_text(case_row))
