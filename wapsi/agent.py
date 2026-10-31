"""The real agent: Claude investigates one quiet merchant with tools.

Try one case with `uv run python -m wapsi.agent C-M0044`. T3 adds the action tools.
"""
import json
import os
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from wapsi import store
from wapsi.tools import READ_TOOLS, SUBMIT_DIAGNOSIS, CaseTools

MAX_TURNS = 12
DEFAULT_MODEL = "claude-sonnet-5-5"

SYSTEM = """You are Wapsi, a Merchant Retention Associate for Paytm's field sales team in India. \
Your job is to find out why a shop using a Paytm device has gone quiet, so the right fix can follow.

A shop gets flagged when its payments fall well below its own normal, or when its device stops \
reporting. Check the evidence before concluding. Your tools describe only this merchant and their \
area, and QR payments can keep arriving when the device itself is offline.

The possible causes:
- device_fault: the device has failed, but the shop is trading normally and signal history is healthy.
- sim_network: the device is offline because of poor connectivity, shown by weak signal or \
  dropouts in the shop's history and area.
- money_problem: settlements are failing, for example a bank or KYC issue.
- billing_anger: the merchant is upset about a charge, such as rent deducted twice.
- competitor_switch: Paytm volume has fallen while nearby shops are normal and nothing is wrong \
  with the device, settlements or billing.
- closed_seasonal: the shop has stopped entirely, and did the same around these dates last year.
- unclear: the evidence does not support one cause, so a human should look.

Report only what the tools show. When you are finished, call submit_diagnosis."""


def as_text(result):
    return json.dumps(result, default=str, ensure_ascii=False)


def run_tool(tools, block):
    """Run one read tool, returning a tool_result. Failures go back to the model."""
    allowed = {tool["name"] for tool in READ_TOOLS}
    if block.name not in allowed:
        return {"type": "tool_result", "tool_use_id": block.id, "is_error": True,
                "content": f"Unknown tool {block.name}. Available: {sorted(allowed)}"}
    return {"type": "tool_result", "tool_use_id": block.id, "content": as_text(getattr(tools, block.name)())}


def record_diagnosis(conn, case_id, diagnosis):
    store.update_case(conn, case_id, cause=diagnosis["cause"], summary=diagnosis["summary"])
    store.add_event(conn, case_id, "status", f"Diagnosis: {diagnosis['cause']}", diagnosis)


def hand_to_human(conn, case_id, reason):
    """Unsure means a person decides, never a guess."""
    diagnosis = {"cause": "unclear", "confidence": "low", "evidence": [], "summary": reason}
    record_diagnosis(conn, case_id, diagnosis)
    return diagnosis


def create_message(client, messages):
    return client.beta.messages.create(
        model=os.environ.get("WAPSI_MODEL", DEFAULT_MODEL),
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        thinking={"type": "adaptive", "display": "summarized"},
        output_config={"effort": "medium"},
        system=SYSTEM,
        tools=[*READ_TOOLS, SUBMIT_DIAGNOSIS],
        messages=messages,
    )


def run_case(conn, case_id, client=None):
    """Investigate one case, record the diagnosis and return it."""
    client = client or anthropic.Anthropic()
    case = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    tools = CaseTools(conn, case["merchant_id"])
    store.update_case(conn, case_id, status="working")
    messages = [{"role": "user", "content": (
        f"Case {case_id}: merchant {case['merchant_id']} was flagged this morning. Recent payment volume "
        f"is {case['volume_ratio']:.0%} of normal, and the device has been offline on "
        f"{case['offline_days']} of the last 3 days. Find out why."
    )}]

    for _ in range(MAX_TURNS):
        response = create_message(client, messages)
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason == "refusal":
            return hand_to_human(conn, case_id, "The agent declined this case, so a person should review it.")

        results = []
        diagnosis = None
        for block in response.content:
            if block.type == "thinking" and block.thinking:
                store.add_event(conn, case_id, "thought", block.thinking)
            elif block.type == "text" and block.text:
                store.add_event(conn, case_id, "thought", block.text)
            elif block.type == "tool_use" and block.name == SUBMIT_DIAGNOSIS["name"]:
                diagnosis = block.input
            elif block.type == "tool_use":
                store.add_event(conn, case_id, "tool_call", block.name)
                result = run_tool(tools, block)
                store.add_event(conn, case_id, "tool_result", block.name, json.loads(result["content"])
                                if not result.get("is_error") else {"error": result["content"]})
                results.append(result)

        if diagnosis:
            record_diagnosis(conn, case_id, diagnosis)
            return diagnosis
        if not results:
            messages.append({"role": "user", "content": "Call submit_diagnosis with your conclusion."})
            continue
        messages.append({"role": "user", "content": results})

    return hand_to_human(conn, case_id, "The agent could not reach a conclusion, so a person should review it.")


if __name__ == "__main__":
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    if not store.db_path().exists():  # Never reset here: a demo may be running.
        store.ensure_db()
    with store.connect() as connection:
        result = run_case(connection, sys.argv[1])
        for event in store.event_rows(connection.execute(
            "SELECT * FROM events WHERE case_id = ? ORDER BY id", (sys.argv[1],)
        )):
            print(f"[{event['kind']}] {event['title'][:300]}")
    print(json.dumps(result, indent=2, ensure_ascii=False))
