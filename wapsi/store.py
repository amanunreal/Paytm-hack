"""Shared state. The agent, voice and API only talk to each other through here."""
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from wapsi import detector, sim

SCHEMA = """
DROP TABLE IF EXISTS cases;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS approvals;
CREATE TABLE cases (
    id TEXT PRIMARY KEY, merchant_id TEXT, cohort TEXT, status TEXT, cause TEXT,
    bucket TEXT, summary TEXT, rep_brief TEXT, volume_ratio REAL, offline_days INTEGER
);
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT, ts TEXT, kind TEXT,
    title TEXT, detail TEXT
);
CREATE TABLE approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT, kind TEXT, amount INTEGER,
    reason TEXT, status TEXT, next_bucket TEXT
);
"""


def db_path():
    return Path(os.environ.get("WAPSI_DB", sim.DB_PATH))


def connect():
    conn = sqlite3.connect(db_path(), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def ensure_db():
    """Build the merchant data on first run and open the 8:00 AM state."""
    path = db_path()
    if not path.exists():
        sim.build(path).close()
    with connect() as conn:
        reset(conn)


def reset(conn):
    """Return to the 8:00 AM state without touching the merchant data."""
    conn.executescript(SCHEMA)
    for item in detector.detect(conn, sim.TODAY):
        status = "new" if item["cohort"] == "ai" else "control"
        conn.execute(
            "INSERT INTO cases VALUES (?, ?, ?, ?, NULL, NULL, NULL, NULL, ?, ?)",
            (f"C-{item['merchant_id']}", item["merchant_id"], item["cohort"], status,
             item["volume_ratio"], item["offline_days"]),
        )
    conn.commit()


def add_event(conn, case_id, kind, title, detail=None):
    conn.execute(
        "INSERT INTO events (case_id, ts, kind, title, detail) VALUES (?, ?, ?, ?, ?)",
        (case_id, datetime.now().isoformat(timespec="seconds"), kind, title, json.dumps(detail)),
    )
    conn.commit()


def update_case(conn, case_id, **fields):
    assignments = ", ".join(f"{name} = ?" for name in fields)
    conn.execute(f"UPDATE cases SET {assignments} WHERE id = ?", (*fields.values(), case_id))
    conn.commit()


def add_approval(conn, case_id, kind, amount, reason, next_bucket):
    conn.execute(
        "INSERT INTO approvals (case_id, kind, amount, reason, status, next_bucket) "
        "VALUES (?, ?, ?, ?, 'pending', ?)",
        (case_id, kind, amount, reason, next_bucket),
    )
    conn.commit()


def rows(cursor):
    return [dict(row) for row in cursor.fetchall()]


def event_rows(cursor):
    events = rows(cursor)
    for event in events:
        event["detail"] = json.loads(event["detail"])
    return events
