import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as Block

from wapsi import actions, agent, store, tools
from wapsi.tools import READ_TOOLS, CaseTools


def tool_use(name, tool_input=None, block_id="t1"):
    return Block(type="tool_use", id=block_id, name=name, input=tool_input or {})


def thinking(text):
    return Block(type="thinking", thinking=text)


def reply(*content, stop_reason="tool_use"):
    return Block(content=list(content), stop_reason=stop_reason)


DIAGNOSIS = {"cause": "device_fault", "confidence": "high", "evidence": ["QR still flowing"],
             "summary": "Box is dead, shop is trading."}
CLOSE = {"outcome": "no_action", "summary": "Nothing to do."}


def finish(block_id="end"):
    return reply(tool_use("record_diagnosis", DIAGNOSIS, f"{block_id}a"), tool_use("close_case", CLOSE, f"{block_id}b"))


class FakeClient:
    """Plays back scripted model replies and records what it was sent."""

    def __init__(self, replies):
        self.replies = iter(replies)
        self.sent = []
        self.beta = Block(messages=Block(create=self.create))

    def create(self, **kwargs):
        self.sent.append(list(kwargs["messages"]))  # The agent keeps appending to its list.
        return next(self.replies)


class AgentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        os.environ["WAPSI_DB"] = str(Path(cls.tmp.name) / "test.db")
        store.ensure_db()

    @classmethod
    def tearDownClass(cls):
        del os.environ["WAPSI_DB"]
        cls.tmp.cleanup()

    def setUp(self):
        self.conn = store.connect()
        store.reset(self.conn)
        self.case_id = self.conn.execute("SELECT id FROM cases WHERE cohort = 'ai' LIMIT 1").fetchone()["id"]

    def tearDown(self):
        self.conn.close()

    def case(self):
        return self.conn.execute("SELECT * FROM cases WHERE id = ?", (self.case_id,)).fetchone()

    def events(self):
        return [e["kind"] for e in store.event_rows(self.conn.execute(
            "SELECT * FROM events WHERE case_id = ? ORDER BY id", (self.case_id,)))]

    def test_loop_investigates_diagnoses_and_closes(self):
        client = FakeClient([reply(thinking("Checking the box"), tool_use("get_device_status")), finish()])
        agent.run_case(self.conn, self.case_id, client)
        self.assertEqual(self.case()["cause"], "device_fault")
        self.assertEqual(self.case()["bucket"], "no_action")
        self.assertEqual(self.case()["status"], "done")
        self.assertEqual(self.events()[:3], ["thought", "tool_call", "tool_result"])

    def test_all_parallel_results_return_in_one_message(self):
        client = FakeClient([
            reply(tool_use("get_billing", block_id="a"), tool_use("get_tickets", block_id="b")),
            finish(),
        ])
        agent.run_case(self.conn, self.case_id, client)
        self.assertEqual([r["tool_use_id"] for r in client.sent[1][-1]["content"]], ["a", "b"])

    def test_unknown_tool_goes_back_to_the_model_as_an_error(self):
        client = FakeClient([reply(tool_use("Get_Billing")), finish()])
        agent.run_case(self.conn, self.case_id, client)
        self.assertTrue(client.sent[1][-1]["content"][0]["is_error"])

    def test_refusal_goes_to_a_human(self):
        agent.run_case(self.conn, self.case_id, FakeClient([reply(stop_reason="refusal")]))
        self.assertEqual(self.case()["status"], "awaiting_approval")

    def test_running_out_of_turns_goes_to_a_human(self):
        client = FakeClient([reply(tool_use("get_tickets")) for _ in range(agent.MAX_TURNS)])
        agent.run_case(self.conn, self.case_id, client)
        self.assertEqual(self.case()["status"], "awaiting_approval")

    def test_a_reply_with_no_tool_call_is_nudged_to_finish(self):
        client = FakeClient([reply(Block(type="text", text="A dead box."), stop_reason="end_turn"), finish()])
        agent.run_case(self.conn, self.case_id, client)
        self.assertEqual(self.case()["status"], "done")

    def test_a_blocked_action_is_logged_and_returned_to_the_model(self):
        client = FakeClient([reply(tool_use("close_case", CLOSE)), finish()])
        agent.run_case(self.conn, self.case_id, client)
        self.assertIn("guardrail", self.events())
        self.assertTrue(client.sent[1][-1]["content"][0]["is_error"])

    def test_control_group_is_never_touched(self):
        control = self.conn.execute("SELECT id FROM cases WHERE cohort = 'control' LIMIT 1").fetchone()["id"]
        with self.assertRaises(ValueError):
            agent.run_case(self.conn, control, FakeClient([]))


class ToolIsolationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        os.environ["WAPSI_DB"] = str(Path(cls.tmp.name) / "test.db")
        store.ensure_db()
        cls.conn = store.connect()
        cls.truth = dict(cls.conn.execute("SELECT merchant_id, scenario FROM ground_truth").fetchall())

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        del os.environ["WAPSI_DB"]
        cls.tmp.cleanup()

    def test_agent_code_never_reads_the_planted_answers(self):
        for module in (agent, tools, actions):
            self.assertNotIn("ground_truth", Path(module.__file__).read_text())

    def test_no_read_tool_reveals_the_answer_the_cohort_or_the_outcome(self):
        merchant_id = next(m for m, s in self.truth.items() if s == "billing_anger")
        case_tools = CaseTools(self.conn, merchant_id)
        text = json.dumps([getattr(case_tools, t["name"])() for t in READ_TOOLS], default=str)
        for secret in ("billing_anger", "cohort", "restart_fixes", "opted_out"):
            self.assertNotIn(secret, text)

    def test_every_read_tool_works_for_every_kind_of_case(self):
        for scenario in set(self.truth.values()):
            merchant_id = next(m for m, s in self.truth.items() if s == scenario)
            case_tools = CaseTools(self.conn, merchant_id)
            for tool in READ_TOOLS:
                json.dumps(getattr(case_tools, tool["name"])(), default=str)

    def test_tools_only_show_their_own_merchant(self):
        tickets = {m for m, s in self.truth.items() if s == "billing_anger"}
        one, other = sorted(tickets)[:2]
        mine = CaseTools(self.conn, one).get_tickets()["tickets"]
        theirs = CaseTools(self.conn, other).get_tickets()["tickets"]
        self.assertEqual(len(mine), 1)
        self.assertNotEqual(mine[0]["body"] + one, theirs[0]["body"] + other)


if __name__ == "__main__":
    unittest.main()
