"""Seeded simulator: 500 merchants with planted reasons for going quiet.

Run with `python3 -m wapsi.sim`. Everything is written to data/wapsi.db.
The ground_truth table is for scoring only: agent tools must never read it.
"""
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

SEED = 7
TODAY = date(2026, 10, 31)  # The 8:00 AM board: data runs up to yesterday.
SIM_VERSION = 2  # Bump when the schema or planted data changes, so old local DBs rebuild.
HISTORY_DAYS = 400  # Over a year, so seasonal closures can be seen.
ONSET_DAYS = 3  # Planted problems started this many days before TODAY.
MERCHANT_COUNT = 500
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "wapsi.db"

# Pan-India: area -> (state, language, typical signal strength).
# A shop is compared with others in its own area, not with the whole country.
AREAS = {
    "Mumbai": ("Maharashtra", "mr", 80),
    "Delhi": ("Delhi", "hi", 82),
    "Bengaluru": ("Karnataka", "kn", 78),
    "Chennai": ("Tamil Nadu", "ta", 80),
    "Kolkata": ("West Bengal", "bn", 76),
    "Hyderabad": ("Telangana", "te", 79),
    "Lucknow": ("Uttar Pradesh", "hi", 74),
    "Jaipur": ("Rajasthan", "hi", 76),
    "Ahmedabad": ("Gujarat", "gu", 78),
    "Pune": ("Maharashtra", "mr", 78),
    "Kochi": ("Kerala", "ml", 77),
    "Patna": ("Bihar", "hi", 70),
    "Ludhiana": ("Punjab", "pa", 75),
    "Bhubaneswar": ("Odisha", "or", 72),
    "Coimbatore": ("Tamil Nadu", "ta", 76),
    "Mysuru": ("Karnataka", "kn", 75),
    "Guwahati": ("Assam", "as", 72),
    "Almora": ("Uttarakhand", "hi", 28),
    "Barmer": ("Rajasthan", "hi", 30),
    "Gumla": ("Jharkhand", "hi", 32),
}
WEAK_SIGNAL_AREAS = {"Almora", "Barmer", "Gumla"}
DIP_AREA = "Guwahati"  # The whole area dips, so Wapsi should do nothing here.
DIP_FACTOR = 0.75

# Planted count per cohort. The AI cohort adds up to the 37 on the cover slide.
SCENARIO_MIX = {
    "device_fault": 7,
    "sim_network": 10,
    "money_problem": 6,
    "billing_anger": 7,
    "competitor_switch": 3,
    "closed_seasonal": 4,
}

SHOP_TYPES = ["Kirana", "Medical", "Chai stall", "Mobile repair", "Sweets", "Tailor", "Dhaba", "Hardware"]
RESTART_FIXES_DEVICE = 2  # Of the 7 device faults in the AI cohort.
RESTART_FAILS_SIM = 2  # Of the 10 SIM problems in the AI cohort.
REPEAT_BILLING_MONTHS = 3

# Language -> (first names, last names).
NAMES = {
    "hi": (["Ramesh", "Sunita", "Manoj", "Geeta", "Vikas", "Pooja", "Rekha", "Deepak"],
           ["Gupta", "Verma", "Yadav", "Maurya", "Pandey", "Sharma"]),
    "mr": (["Sachin", "Vaishali", "Ganesh", "Sunanda"], ["Patil", "Jadhav", "Shinde", "Kulkarni"]),
    "kn": (["Manjunath", "Lakshmi", "Basavaraj", "Shobha"], ["Gowda", "Hegde", "Shetty", "Naik"]),
    "ta": (["Murugan", "Selvi", "Karthik", "Revathi"], ["Pillai", "Mudaliar", "Nadar", "Chettiar"]),
    "bn": (["Subrata", "Mitali", "Anirban", "Rina"], ["Das", "Ghosh", "Mondal", "Sarkar"]),
    "te": (["Srinivas", "Padma", "Venkat", "Anjali"], ["Reddy", "Rao", "Naidu", "Goud"]),
    "gu": (["Jignesh", "Hetal", "Bhavesh", "Kinjal"], ["Patel", "Shah", "Desai", "Parmar"]),
    "ml": (["Biju", "Sreeja", "Shaji", "Mini"], ["Nair", "Menon", "Varghese", "Pillai"]),
    "pa": (["Gurpreet", "Harleen", "Balwinder", "Simran"], ["Gill", "Sandhu", "Dhillon", "Grewal"]),
    "or": (["Prakash", "Sasmita", "Bikash", "Mamata"], ["Mohanty", "Sahu", "Behera", "Nayak"]),
    "as": (["Bhaskar", "Pranjal", "Jonali", "Rupam"], ["Baruah", "Bora", "Kalita", "Saikia"]),
}
# Whole names, because these do not pair freely with the surnames above.
URDU_NAMES = ["Mohd. Irfan Khan", "Nasreen Khan", "Salim Ansari", "Shabana Ansari"]

SCHEMA = """
CREATE TABLE merchants (
    id TEXT PRIMARY KEY, owner TEXT, shop_type TEXT, area TEXT, state TEXT, language TEXT,
    phone TEXT, device_model TEXT, monthly_rent INTEGER, cohort TEXT,
    opted_out INTEGER DEFAULT 0
);
CREATE TABLE daily (
    merchant_id TEXT, day TEXT, txn_count INTEGER, gmv INTEGER,
    heartbeats INTEGER, signal INTEGER, PRIMARY KEY (merchant_id, day)
);
CREATE TABLE settlements (
    merchant_id TEXT, day TEXT, amount INTEGER, status TEXT, reason TEXT
);
CREATE TABLE billing (
    merchant_id TEXT, day TEXT, kind TEXT, amount INTEGER, note TEXT
);
CREATE TABLE tickets (
    merchant_id TEXT, opened TEXT, category TEXT, status TEXT, body TEXT
);
CREATE TABLE ground_truth (merchant_id TEXT PRIMARY KEY, scenario TEXT);
CREATE TABLE world (merchant_id TEXT PRIMARY KEY, restart_fixes INTEGER);
CREATE INDEX daily_day ON daily (day);
"""


def build_merchants(rng):
    """Create merchants, then assign cohorts and planted scenarios."""
    merchants = []
    areas = list(AREAS)
    for i in range(MERCHANT_COUNT):
        area = areas[i % len(areas)]
        state, language, _ = AREAS[area]
        first_names, last_names = NAMES[language]
        owner = f"{rng.choice(first_names)} {rng.choice(last_names)}"
        if language == "hi" and rng.random() < 0.15:
            owner = rng.choice(URDU_NAMES)
        merchants.append({
            "id": f"M{i + 1:04d}",
            "owner": owner,
            "shop_type": rng.choice(SHOP_TYPES),
            "area": area,
            "state": state,
            "language": language,
            "phone": f"+91900000{i + 1:04d}",
            "device_model": rng.choice(["Soundbox 4G", "Soundbox 4G", "Soundbox WiFi", "AI Soundbox"]),
            "monthly_rent": rng.choice([80, 100, 118, 135]),
            "cohort": rng.choice(["ai", "control"]),
            "base_txns": rng.randint(15, 120),
            "avg_ticket": rng.randint(80, 350),
            "closed_sundays": rng.random() < 0.2,
            "scenario": None,
            "restart_fixes": True,
            "repeat_billing": False,
        })

    weak = [m for m in merchants if m["area"] in WEAK_SIGNAL_AREAS]
    clean = [m for m in merchants if m["area"] not in WEAK_SIGNAL_AREAS and m["area"] != DIP_AREA]
    rng.shuffle(weak)
    rng.shuffle(clean)
    for cohort in ("ai", "control"):
        for scenario, count in SCENARIO_MIX.items():
            pool = weak if scenario == "sim_network" else clean
            for _ in range(count):
                picked = pool.pop()
                picked["cohort"] = cohort
                picked["scenario"] = scenario
    for merchant in merchants:
        if merchant["area"] == DIP_AREA:
            merchant["scenario"] = "area_dip"
    plant_outcomes(merchants)
    return merchants


def plant_outcomes(merchants):
    """Decide how the world responds to the agent. Sorted, so reruns stay identical."""
    def ai(scenario):
        return sorted(
            (m for m in merchants if m["cohort"] == "ai" and m["scenario"] == scenario),
            key=lambda m: m["id"],
        )

    # A restart fixes only some boxes. The others need a visit with new hardware.
    for merchant in ai("device_fault")[:-RESTART_FIXES_DEVICE]:
        merchant["restart_fixes"] = False
    for merchant in ai("sim_network")[:RESTART_FAILS_SIM]:
        merchant["restart_fixes"] = False
    # One merchant was overcharged for months, which is more than the agent may refund.
    next(m for m in ai("billing_anger") if m["monthly_rent"] == 135)["repeat_billing"] = True


def simulate_day(rng, merchant, day):
    """Return (txn_count, gmv, heartbeats, signal) for one merchant on one day."""
    scenario = merchant["scenario"]
    days_ago = (TODAY - day).days
    started = days_ago <= ONSET_DAYS
    weak_area = merchant["area"] in WEAK_SIGNAL_AREAS
    typical_signal = AREAS[merchant["area"]][2]

    txns = merchant["base_txns"] * rng.gauss(1, 0.15)
    if merchant["closed_sundays"] and day.weekday() == 6:
        txns = 0
    elif rng.random() < 0.01:
        txns = 0  # An ordinary day off.

    heartbeats = 24
    signal = max(5, min(99, round(rng.gauss(typical_signal, 6))))
    if weak_area and rng.random() < 0.02:
        heartbeats = 0
    elif rng.random() < 0.002:
        heartbeats = 0

    if scenario == "closed_seasonal":
        # Closed for the same weeks every year.
        last_year = (TODAY - timedelta(days=365) - day).days
        if started or -ONSET_DAYS - 20 <= last_year <= ONSET_DAYS:
            txns, heartbeats = 0, 0
    elif started:
        if scenario == "device_fault":
            heartbeats = 0
        elif scenario == "sim_network":
            heartbeats, txns = 0, txns * 0.9
        elif scenario in ("money_problem", "billing_anger"):
            txns *= 0.4
        elif scenario == "competitor_switch":
            txns *= 0.3
        elif scenario == "area_dip":
            txns *= DIP_FACTOR

    txns = round(txns)
    if heartbeats == 0:
        signal = None
    return txns, txns * merchant["avg_ticket"], heartbeats, signal


def plant_records(rng, merchant, conn):
    """Add the billing, settlement and ticket clues for a planted scenario."""
    scenario = merchant["scenario"]
    start = TODAY - timedelta(days=ONSET_DAYS)
    rent = merchant["monthly_rent"]
    if scenario == "money_problem":
        reason = rng.choice(["IFSC mismatch", "KYC re-verification pending", "Bank account inactive"])
        amount = 0
        for offset in range(ONSET_DAYS):
            day = (start + timedelta(days=offset)).isoformat()
            amount = merchant["base_txns"] * merchant["avg_ticket"]
            conn.execute("INSERT INTO settlements VALUES (?, ?, ?, 'failed', ?)", (merchant["id"], day, amount, reason))
        conn.execute(
            "INSERT INTO tickets VALUES (?, ?, 'settlement', 'open', ?)",
            (merchant["id"], start.isoformat(), f"Payment not received in bank for {ONSET_DAYS} days"),
        )
    elif scenario == "billing_anger":
        months = REPEAT_BILLING_MONTHS if merchant["repeat_billing"] else 1
        first_of_month = TODAY.replace(day=1)
        for _ in range(months):
            conn.execute(
                "INSERT INTO billing VALUES (?, ?, 'rent_duplicate', ?, 'Second rent cut from settlement this month')",
                (merchant["id"], first_of_month.isoformat(), rent),
            )
            first_of_month = (first_of_month - timedelta(days=1)).replace(day=1)
        body = f"Rs {rent} rent cut twice from my settlement, no message received"
        if months > 1:
            body = f"Rs {rent} rent cut twice every month for {months} months, no message received"
        conn.execute(
            "INSERT INTO tickets VALUES (?, ?, 'billing', 'open', ?)",
            (merchant["id"], start.isoformat(), body),
        )


def build(db_path=DB_PATH, seed=SEED):
    rng = random.Random(seed)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    for suffix in ("", "-wal", "-shm"):
        Path(f"{db_path}{suffix}").unlink(missing_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)

    merchants = build_merchants(rng)
    days = [TODAY - timedelta(days=n) for n in range(HISTORY_DAYS, 0, -1)]
    months = sorted({day.replace(day=1) for day in days})[-6:]
    for merchant in merchants:
        conn.execute(
            "INSERT INTO merchants (id, owner, shop_type, area, state, language, phone, device_model, "
            "monthly_rent, cohort) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            tuple(merchant[k] for k in ("id", "owner", "shop_type", "area", "state", "language", "phone",
                                        "device_model", "monthly_rent", "cohort")),
        )
        conn.executemany(
            "INSERT INTO daily VALUES (?, ?, ?, ?, ?, ?)",
            [(merchant["id"], day.isoformat(), *simulate_day(rng, merchant, day)) for day in days],
        )
        conn.executemany(
            "INSERT INTO billing VALUES (?, ?, 'rent', ?, 'Monthly device rent')",
            [(merchant["id"], month.isoformat(), merchant["monthly_rent"]) for month in months],
        )
        conn.execute("INSERT INTO world VALUES (?, ?)", (merchant["id"], merchant["restart_fixes"]))
        if merchant["scenario"]:
            conn.execute("INSERT INTO ground_truth VALUES (?, ?)", (merchant["id"], merchant["scenario"]))
            plant_records(rng, merchant, conn)
    conn.execute(f"PRAGMA user_version = {SIM_VERSION}")
    conn.commit()
    return conn


if __name__ == "__main__":
    connection = build()
    for scenario, count in connection.execute(
        "SELECT scenario, COUNT(*) FROM ground_truth GROUP BY scenario ORDER BY scenario"
    ):
        print(f"{scenario:20} {count}")
    print("merchants", connection.execute("SELECT COUNT(*) FROM merchants").fetchone()[0])
    print("db", DB_PATH)
