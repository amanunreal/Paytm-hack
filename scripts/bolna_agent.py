"""Set up and test the Bolna Hindi agent. A2 owns this file.

  uv run python scripts/bolna_agent.py create   # prints the id for BOLNA_AGENT_ID
  uv run python scripts/bolna_agent.py update   # pushes this file's config to the agent
  uv run python scripts/bolna_agent.py setup-outcome   # post-call fixed / not fixed answer
  uv run python scripts/bolna_agent.py call     # rings DEMO_MERCHANT_PHONE once

The API reference: https://www.bolna.ai/docs/api-reference/introduction
Text stays in Devanagari, because Sarvam's bulbul:v4-flash speaks the script it is given.
"""
import os
import re
import sys
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.bolna.ai"
AGENT_NAME = "Wapsi Hindi"
# Must match wapsi/voice.py, which reads this answer after the call.
OUTCOME_CATEGORY = "Wapsi"
OUTCOME_NAME = "Call Outcome"
POLL_SECONDS = 3
POLL_LIMIT_SECONDS = 300
# call-disconnected is not here: cost and transcript are not final until completed.
TERMINAL = {"completed", "no-answer", "busy", "canceled", "failed", "stopped", "error", "balance-low"}

# The hero case from PLAN.md. T9 builds this from the case instead.
DEMO_MERCHANT = {
    "merchant_name": "सुनीता",
    "shop_type": "टेलरिंग",
    "area": "अल्मोड़ा",
    "offline_days": "3",
}

WELCOME = (
    "नमस्ते {merchant_name} जी, मैं पेटीएम की AI सहायक वापसी बोल रही हूँ। "
    "आपका साउंडबॉक्स {offline_days} दिन से ऑफ़लाइन है। क्या दो मिनट बात हो सकती है?"
)

SYSTEM_PROMPT = """आप वापसी हैं, पेटीएम की AI सहायक। आप {merchant_name} जी से फ़ोन पर हिंदी में बात कर रही हैं।
उनकी {shop_type} की दुकान {area} में है।

स्थिति: उनका साउंडबॉक्स {offline_days} दिन से ऑफ़लाइन है, पर QR से भुगतान सामान्य रूप से आ रहे हैं। यानी पैसे आ रहे हैं, और दिक़्क़त सिम या नेटवर्क की लगती है।

बातचीत का क्रम:
1. बताइए कि उनके पैसे सुरक्षित हैं और भुगतान आ रहे हैं।
2. पूछिए कि क्या साउंडबॉक्स से भुगतान की आवाज़ नहीं आ रही।
3. उनसे कहिए कि पावर बटन दबाए रखें जब तक डिब्बा बंद न हो जाए, 10 सेकंड रुकें, फिर पावर बटन दबाकर चालू करें। उनके करने तक रुकिए।
4. पूछिए कि क्या बत्ती जली और डिब्बा चालू हो गया।
5. ठीक हो गया तो एक बार धन्यवाद कहिए। नहीं हुआ तो बताइए कि हमारा प्रतिनिधि संपर्क करेगा।

नियम:
- हर बार एक या दो छोटे वाक्य बोलिए, और एक बार में एक ही बात पूछिए।
- अगर वे अभी बात न कर सकें या बाद में कॉल करने को कहें, तो कहिए कि हम दोबारा कॉल करेंगे, और बात ख़त्म कीजिए।
- कभी बैंक खाता, IFSC, OTP, PIN या कार्ड की जानकारी न माँगिए, न सुनिए, न बताइए। अगर वे बताने लगें तो विनम्रता से रोकिए और कहिए कि यह काम पेटीएम ऐप के सत्यापित तरीक़े से ही होता है।
- अगर वे पूछें कि बंद कैसे करें, तो तीसरा क़दम धीरे से समझाइए। बटन की जगह आपको नहीं पता, इसलिए डिब्बे पर पावर के निशान वाला बटन ढूँढने को कहिए। दो बार समझाने पर भी न हो, तभी कहिए कि हमारा प्रतिनिधि संपर्क करेगा।
- अगर वे कहें कि रीस्टार्ट कर दिया, तो सीधे चौथे क़दम पर जाइए।
- विदा लेने के बाद कोई नया सवाल मत पूछिए, और जो कह चुकी हैं उसे मत दोहराइए।
- कोई छूट, रिफ़ंड या शुल्क माफ़ी का वादा मत कीजिए।
- पूछे जाने पर साफ़ बताइए कि आप AI हैं। वे इंसान से बात करना चाहें तो कहिए कि हमारी टीम उन्हें कॉल करेगी।"""

HANGUP_PROMPT = (
    "End the call only if the agent has already said goodbye or thanked the merchant to close "
    "the call: the box is fixed, a representative will contact them, or the agent will call "
    "again later. Do not end it while the agent is waiting for the merchant to restart the box "
    "or has just asked a question."
)


def client():
    key = os.environ.get("BOLNA_API_KEY", "").strip()
    if not key:
        sys.exit("BOLNA_API_KEY is empty in .env")
    return httpx.Client(base_url=BASE_URL, timeout=30, headers={"Authorization": f"Bearer {key}"})


def agent_payload():
    tools = {
        "llm_agent": {
            "agent_type": "simple_llm_agent",
            "agent_flow_type": "streaming",
            "llm_config": {"provider": "openai", "model": "gpt-4.1-mini", "max_tokens": 150, "temperature": 0.2},
        },
        "transcriber": {
            "provider": "sarvam",
            "model": "saaras:v4",
            "language": "hi",
            "stream": True,
            "endpointing": 500,
            "context": "A Paytm merchant in India is on a support call about a Soundbox that has gone offline.",
        },
        "synthesizer": {
            "provider": "sarvam",
            "provider_config": {
                "voice": "Aparna (Customer)",
                "voice_id": "aparna_hi_customer",
                "model": "bulbul:v4-flash",
                "language": "hi",
                "speed": 1.0,
            },
            "stream": True,
            "buffer_size": 150,
        },
        "input": {"provider": "plivo", "format": "wav"},
        "output": {"provider": "plivo", "format": "wav"},
    }
    return {
        "agent_config": {
            "agent_name": AGENT_NAME,
            "agent_welcome_message": WELCOME,
            "tasks": [{
                "task_type": "conversation",
                "toolchain": {"execution": "sequential", "pipelines": [["transcriber", "llm", "synthesizer"]]},
                "tools_config": tools,
                # Long silences on purpose: the merchant goes quiet while restarting the box.
                "task_config": {
                    "call_terminate": 180,
                    "hangup_after_silence": 30,
                    "hangup_after_LLMCall": True,
                    "call_cancellation_prompt": HANGUP_PROMPT,
                    "call_hangup_message": "धन्यवाद, नमस्ते।",
                    # One word let noise cut the agent off mid-sentence.
                    "number_of_words_for_interruption": 2,
                    "trigger_user_online_message_after": 20,
                    # Not in Bolna's docs, but the live agent has it. The default is English.
                    "check_user_online_message": "क्या आप लाइन पर हैं?",
                },
            }],
        },
        "agent_prompts": {"task_1": {"system_prompt": SYSTEM_PROMPT}},
    }


def create():
    with client() as bolna:
        response = bolna.get("/v2/agent/all")
        response.raise_for_status()
        existing = [agent for agent in response.json() if agent.get("agent_name") == AGENT_NAME]
        if existing:
            print(f"Already exists, reusing it. BOLNA_AGENT_ID={existing[0]['id']}")
            return
        response = bolna.post("/v2/agent", json=agent_payload())
        if response.status_code >= 400:
            sys.exit(f"Create failed with {response.status_code}: {response.text}")
        print(f"BOLNA_AGENT_ID={response.json()['agent_id']}")


def setup_outcome():
    """Make the post-call extraction that wapsi/voice.py reads to pick the next step."""
    agent_id = agent_id_from_env()
    with client() as bolna:
        response = bolna.get("/dispositions/", params={"agent_id": agent_id})
        response.raise_for_status()
        if OUTCOME_NAME in response.text:
            print("Outcome extraction already exists")
            return
        response = bolna.post("/dispositions/", json={
            "agent_id": agent_id,
            "name": OUTCOME_NAME,
            "category": OUTCOME_CATEGORY,
            "question": (
                "This is a Hindi support call about a Paytm Soundbox that went offline. Decide whether "
                "the merchant's box came back. Only trust what the merchant says, not what the agent "
                "assumes. If the call ended before the merchant confirmed the result, it is not fixed."
            ),
            "is_objective": True,
            "objective_options": [
                {"value": "fixed", "condition": "The merchant clearly confirms the box is back on or working."},
                {"value": "not_fixed", "condition": (
                    "The merchant tried the restart and the box still does not work, or says they "
                    "cannot do it, or asks for someone to come."
                )},
                {"value": "call_back", "condition": (
                    "The merchant is busy, asks to be called later, or the call stopped before the "
                    "restart was finished."
                )},
                {"value": "NA", "condition": "None of the above is clear from the call."},
            ],
            "is_subjective": False,
            "subjective_type": "text",
        })
        if response.status_code >= 400:
            sys.exit(f"Setup failed with {response.status_code}: {response.text}")
        print("Outcome extraction created")


def agent_id_from_env():
    agent_id = os.environ.get("BOLNA_AGENT_ID", "").strip()
    if not agent_id:
        sys.exit("BOLNA_AGENT_ID is empty in .env. Run the create command first.")
    return agent_id


def update():
    with client() as bolna:
        response = bolna.put(f"/v2/agent/{agent_id_from_env()}", json=agent_payload())
        if response.status_code >= 400:
            sys.exit(f"Update failed with {response.status_code}: {response.text}")
        print("Agent updated")


def call():
    agent_id = agent_id_from_env()
    phone = os.environ.get("DEMO_MERCHANT_PHONE", "").strip()
    if not re.fullmatch(r"\+[1-9]\d{7,14}", phone):
        sys.exit("DEMO_MERCHANT_PHONE in .env must include the country code, e.g. +9198XXXXXXXX")
    with client() as bolna:
        response = bolna.post("/call", json={
            "agent_id": agent_id,
            "recipient_phone_number": phone,
            "user_data": DEMO_MERCHANT,
        })
        if response.status_code >= 400:
            sys.exit(f"Call failed with {response.status_code}: {response.text}")
        execution_id = response.json()["execution_id"]
        print(f"Queued {execution_id}")

        status = None
        deadline = time.monotonic() + POLL_LIMIT_SECONDS
        while time.monotonic() < deadline:
            time.sleep(POLL_SECONDS)
            response = bolna.get(f"/executions/{execution_id}")
            response.raise_for_status()
            execution = response.json()
            if execution.get("status") != status:
                status = execution.get("status")
                print(f"Status: {status}")
            if status in TERMINAL:
                break
        else:
            sys.exit(f"Gave up waiting after {POLL_LIMIT_SECONDS}s. Last status: {status}")

    print(f"Duration: {execution.get('conversation_duration')}s, cost: {execution.get('total_cost')} cents")
    print(f"Ended by: {execution.get('termination_reason')}")
    if execution.get("error_message"):
        print(f"Error: {execution['error_message']}")
    print(f"Transcript:\n{execution.get('transcript')}")
    if status != "completed":
        sys.exit(1)


if __name__ == "__main__":
    commands = {"create": create, "update": update, "setup-outcome": setup_outcome, "call": call}
    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        sys.exit(f"Usage: bolna_agent.py [{' | '.join(commands)}]")
    commands[sys.argv[1]]()
