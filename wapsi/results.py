"""AI group vs control. Outcomes are simulated from the assumptions below."""
from wapsi.sim import TODAY

# What one device merchant earns Paytm a year, rounded down from public Q1 FY27 numbers:
# (net payment revenue Rs 601 Cr + financial services Rs 814 Cr) x 4 / 1.57 Cr = Rs 3,605.
YEARLY_VALUE = 3000
VISIT_COST = 72.5  # Midpoint of Rs 55-90.
CALL_COST = 12.5  # Midpoint of Rs 10-15.

# Chance a merchant is back at 70% of normal after 7 days: (with Wapsi, control).
RECOVERY = {
    "device_fault": (0.85, 0.35),
    "sim_network": (0.80, 0.40),
    "money_problem": (0.80, 0.30),
    "billing_anger": (0.70, 0.20),
    "competitor_switch": (0.35, 0.10),
}


def results(conn):
    truth = dict(conn.execute("SELECT merchant_id, scenario FROM ground_truth").fetchall())
    cases = conn.execute("SELECT merchant_id, cohort, bucket FROM cases").fetchall()
    ai = [c for c in cases if c["cohort"] == "ai" and truth.get(c["merchant_id"]) in RECOVERY]
    control = [c for c in cases if c["cohort"] == "control" and truth.get(c["merchant_id"]) in RECOVERY]

    ai_won = sum(RECOVERY[truth[c["merchant_id"]]][0] for c in ai)
    control_won = sum(RECOVERY[truth[c["merchant_id"]]][1] for c in control)
    ai_visits = sum(1 for c in ai if c["bucket"] == "rep_visit")
    ai_cost = ai_visits * VISIT_COST + len(ai) * CALL_COST
    control_cost = len(control) * VISIT_COST  # Today, every case costs a visit.
    return {
        "simulated": True,
        "as_of": TODAY.isoformat(),
        "ai": {"merchants": len(ai), "won_back": round(ai_won, 1), "visits": ai_visits, "cost": round(ai_cost)},
        "control": {"merchants": len(control), "won_back": round(control_won, 1),
                    "visits": len(control), "cost": round(control_cost)},
        "incremental_won_back": round(ai_won - control_won, 1),
        "revenue_kept": round((ai_won - control_won) * YEARLY_VALUE),
        "assumptions": {"recovery_with_wapsi_vs_control": RECOVERY, "yearly_value": YEARLY_VALUE,
                        "visit_cost": VISIT_COST, "call_cost": CALL_COST},
    }
