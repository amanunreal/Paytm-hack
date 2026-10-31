"""Flag merchants who have gone quiet, each measured against their own normal.

Uses only payment and device data, never ground_truth. A dip that matches the
merchant's area is not flagged, which is how Wapsi knows to do nothing.
"""
from collections import defaultdict
from datetime import date, timedelta
from statistics import median

RECENT_DAYS = 3
BASELINE_WEEKS = 4
QUIET_RATIO = 0.6  # Flag below 60% of normal after adjusting for the area.
OFFLINE_DAYS = 2  # Flag after this many straight days with no heartbeat.
AREA_DIP_RATIO = 0.85  # An area median below this is a shared dip.


def scan(conn, today):
    """Return volume ratios, heartbeats and area context for every merchant."""
    start = today - timedelta(days=RECENT_DAYS + BASELINE_WEEKS * 7)
    rows = conn.execute(
        "SELECT merchant_id, day, txn_count, heartbeats FROM daily WHERE day >= ?",
        (start.isoformat(),),
    )
    txns = defaultdict(dict)
    heartbeats = defaultdict(dict)
    for merchant_id, day, txn_count, beats in rows:
        day = date.fromisoformat(day)
        txns[merchant_id][day] = txn_count
        heartbeats[merchant_id][day] = beats

    recent = [today - timedelta(days=n) for n in range(1, RECENT_DAYS + 1)]
    ratios = {}
    for merchant_id, history in txns.items():
        # Same weekdays only, so a Sunday closure does not look like a drop.
        # A zero day is a day off, unless every recent day is zero. The median
        # of the rest means one slow day does not flag anyone either.
        day_ratios = []
        for day in recent:
            normal = sum(
                history.get(day - timedelta(weeks=week), 0)
                for week in range(1, BASELINE_WEEKS + 1)
            ) / BASELINE_WEEKS
            if normal > 0:
                day_ratios.append(history.get(day, 0) / normal)
        if day_ratios:
            ratios[merchant_id] = median([r for r in day_ratios if r > 0] or [0])

    merchants = dict(conn.execute("SELECT id, area FROM merchants").fetchall())
    cohorts = dict(conn.execute("SELECT id, cohort FROM merchants").fetchall())
    by_area = defaultdict(list)
    for merchant_id, ratio in ratios.items():
        by_area[merchants[merchant_id]].append(ratio)
    area_ratios = {area: median(values) for area, values in by_area.items()}
    return ratios, heartbeats, merchants, cohorts, area_ratios, by_area


def area_dips(conn, today):
    """Return areas that dipped together, which Wapsi deliberately leaves alone."""
    _, _, _, _, area_ratios, by_area = scan(conn, today)
    return [
        {"area": area, "ratio": round(ratio, 2), "merchants": len(by_area[area])}
        for area, ratio in area_ratios.items()
        if ratio < AREA_DIP_RATIO
    ]


def detect(conn, today):
    """Return flagged merchants for the morning of `today`, quietest first."""
    ratios, heartbeats, merchants, cohorts, area_ratios, _ = scan(conn, today)
    recent = [today - timedelta(days=n) for n in range(1, RECENT_DAYS + 1)]

    flagged = []
    for merchant_id, ratio in ratios.items():
        area_ratio = area_ratios[merchants[merchant_id]]
        relative = ratio / area_ratio if area_ratio else ratio
        offline = sum(1 for day in recent if heartbeats[merchant_id].get(day, 0) == 0)
        recent_two_offline = all(
            heartbeats[merchant_id].get(today - timedelta(days=n), 0) == 0
            for n in range(1, OFFLINE_DAYS + 1)
        )
        if relative < QUIET_RATIO or recent_two_offline:
            flagged.append({
                "merchant_id": merchant_id,
                "cohort": cohorts[merchant_id],
                "volume_ratio": round(ratio, 2),
                "area_ratio": round(area_ratio, 2),
                "offline_days": offline,
            })
    return sorted(flagged, key=lambda item: item["volume_ratio"])
