"""What the agent can see. Each instance is bound to one merchant.

Tools take no merchant id, so the model cannot wander to other merchants. Nothing here
reads the planted answers, and merchant cohort is never returned.
"""
from datetime import timedelta
from statistics import mean, median

from wapsi import detector, sim
from wapsi.detector import OFFLINE_DAYS

CAUSES = [
    "device_fault",
    "sim_network",
    "money_problem",
    "billing_anger",
    "competitor_switch",
    "closed_seasonal",
    "unclear",
]


SIGNAL_SCALE = "Signal is a 0 to 100 score, where a healthy device is around 70 or more and below 40 is weak."


def read_only(name, description):
    return {
        "name": name,
        "description": description,
        "strict": True,
        "input_schema": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
    }


READ_TOOLS = [
    read_only("get_merchant", "The shop's profile: owner, type, area, state, language, device and rent."),
    read_only("get_payments", "Daily payment counts for the last 14 days, including QR payments, which keep "
                              "arriving even when the device is offline."),
    read_only("get_device_status", "Device heartbeats and signal strength for the last 14 days, plus the "
                                   f"shop's own signal history over the last 60 days. {SIGNAL_SCALE}"),
    read_only("get_settlements", "Failed settlements for this shop, with the reason."),
    read_only("get_billing", "Rent and other charges over the last 6 months."),
    read_only("get_tickets", "Support tickets this merchant has raised."),
    read_only("get_area_context", "How other shops in this merchant's area are doing right now: volume "
                                  f"against their normal, offline devices and typical signal. {SIGNAL_SCALE}"),
    read_only("get_last_year", "This shop's payments and device activity around the same dates last year."),
]

SUBMIT_DIAGNOSIS = {
    "name": "submit_diagnosis",
    "description": "Record your conclusion for this case. Call this once, when you are finished investigating.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "cause": {"type": "string", "enum": CAUSES,
                      "description": "Use unclear when the evidence does not support one cause."},
            "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
            "evidence": {"type": "array", "items": {"type": "string"},
                         "description": "The specific facts from the tools that support the cause."},
            "summary": {"type": "string",
                        "description": "One plain sentence a field manager can read at a glance."},
        },
        "required": ["cause", "confidence", "evidence", "summary"],
        "additionalProperties": False,
    },
}


class CaseTools:
    """Read-only views of one merchant's data, as of the morning of `today`."""

    def __init__(self, conn, merchant_id, today=sim.TODAY):
        self.conn = conn
        self.merchant_id = merchant_id
        self.today = today

    def since(self, days):
        return (self.today - timedelta(days=days)).isoformat()

    def daily(self, start, end, columns):
        return [dict(row) for row in self.conn.execute(
            f"SELECT {columns} FROM daily WHERE merchant_id = ? AND day >= ? AND day < ? ORDER BY day",
            (self.merchant_id, start, end),
        )]

    def get_merchant(self):
        return dict(self.conn.execute(
            "SELECT id, owner, shop_type, area, state, language, device_model, monthly_rent "
            "FROM merchants WHERE id = ?", (self.merchant_id,),
        ).fetchone())

    def get_payments(self):
        return {"last_14_days": self.daily(self.since(14), self.today.isoformat(), "day, txn_count, gmv")}

    def get_device_status(self):
        history = self.daily(self.since(60), self.today.isoformat(), "day, heartbeats, signal")
        signals = [row["signal"] for row in history if row["signal"] is not None]
        return {
            "last_14_days": history[-14:],
            "average_signal_60_days": round(mean(signals)) if signals else None,
            "days_with_no_heartbeat_60_days": sum(1 for row in history if row["heartbeats"] == 0),
        }

    def get_settlements(self):
        failed = [dict(row) for row in self.conn.execute(
            "SELECT day, amount, status, reason FROM settlements WHERE merchant_id = ? ORDER BY day",
            (self.merchant_id,),
        )]
        return {"failed_settlements": failed}

    def get_billing(self):
        return {"charges": [dict(row) for row in self.conn.execute(
            "SELECT day, kind, amount, note FROM billing WHERE merchant_id = ? ORDER BY day",
            (self.merchant_id,),
        )]}

    def get_tickets(self):
        return {"tickets": [dict(row) for row in self.conn.execute(
            "SELECT opened, category, status, body FROM tickets WHERE merchant_id = ? ORDER BY opened",
            (self.merchant_id,),
        )]}

    def get_area_context(self):
        ratios, heartbeats, areas, _, area_ratios, _ = detector.scan(self.conn, self.today)
        area = areas[self.merchant_id]
        peers = [m for m, peer_area in areas.items() if peer_area == area and m != self.merchant_id]
        recent = [self.today - timedelta(days=n) for n in range(1, OFFLINE_DAYS + 1)]
        offline = sum(1 for m in peers if all(heartbeats[m].get(day, 0) == 0 for day in recent))
        signals = [row[0] for row in self.conn.execute(
            f"SELECT signal FROM daily WHERE day >= ? AND signal IS NOT NULL AND merchant_id IN "
            f"({','.join('?' * len(peers))})", (self.since(7), *peers),
        )]
        return {
            "area": area,
            "shops_in_area": len(peers),
            "median_volume_vs_normal": round(median(ratios[m] for m in peers if m in ratios), 2),
            "shops_offline_now": offline,
            "average_signal": round(mean(signals)) if signals else None,
        }

    def get_last_year(self):
        anchor = self.today - timedelta(days=365)
        rows = self.daily((anchor - timedelta(days=7)).isoformat(), (anchor + timedelta(days=8)).isoformat(),
                          "day, txn_count, heartbeats")
        return {"around_same_dates_last_year": rows}
