"""Load and preprocess hackathon datasets into compact JSON for the demo."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from config import (
    ALARMS_CSV,
    AURORA_SMARTTI,
    BUILDINGS,
    DATA_DIR,
    MAINTENANCE_CSV,
    WORK_ORDERS_CSV,
)


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _parse_dt(value: str | None) -> datetime | None:
    if not value or (isinstance(value, float) and pd.isna(value)):
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S+00"):
        try:
            dt = datetime.strptime(str(value).split("+")[0].strip(), fmt.split("+")[0])
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        return pd.to_datetime(value, utc=True).to_pydatetime()
    except Exception:
        return None


def _extract_location(description: str) -> str:
    """Pull a short location token from Finnish alarm descriptions."""
    if not description:
        return "Unknown"
    # Common patterns: equipment codes like JJ01TE55, room codes
    code = re.search(r"\b[A-Z]{2}\d{2}[A-Z]{2}\d{2}\b", description)
    if code:
        return code.group(0)
    short = description.split(",")[0].strip()
    return short[:60] if len(short) > 60 else short


def process_lentokentankatu() -> dict[str, Any]:
    site = BUILDINGS["lentokentankatu_11"]["site_match"]
    alarms = pd.read_csv(ALARMS_CSV, encoding="utf-8-sig")
    alarms = alarms[alarms["CUSTOMER_SITE_NAME"] == site].copy()
    alarms["dt"] = pd.to_datetime(alarms["EVENT_TIME"], utc=True)

    weekly = (
        alarms.set_index("dt")
        .resample("W-SUN")
        .size()
        .rename("count")
        .reset_index()
    )
    weekly["week_start"] = weekly["dt"].dt.strftime("%Y-%m-%d")
    weekly_list = [
        {"week_start": row.week_start, "count": int(row.count)}
        for row in weekly.itertuples()
        if row.count > 0 or row.dt >= weekly["dt"].max() - pd.Timedelta(weeks=8)
    ]

    # Recent actionable alarms (non log-only)
    recent = alarms[alarms["dt"] >= alarms["dt"].max() - pd.Timedelta(days=90)]
    actionable = recent[recent["LOG_ONLY"].isna() | (recent["LOG_ONLY"] != "L")]

    alarm_records = []
    for row in actionable.sort_values("dt", ascending=False).head(200).itertuples():
        alarm_records.append(
            {
                "id": int(row.ALERT_EVENT_ID),
                "time": row.dt.isoformat(),
                "priority": int(row.Priority),
                "alert_type": str(row.ALERT_TYPE) if pd.notna(row.ALERT_TYPE) else "UNKNOWN",
                "description": str(row.EVENT_DESCRIPTION)[:300],
                "location_hint": _extract_location(str(row.EVENT_DESCRIPTION)),
                "hwid_type": str(row.HWID_TYPE) if pd.notna(row.HWID_TYPE) else "",
            }
        )

    type_counts = Counter(actionable["ALERT_TYPE"].dropna().astype(str))
    location_counts = Counter(
        _extract_location(str(d)) for d in actionable["EVENT_DESCRIPTION"]
    )

    # Work orders — semicolon delimiter
    wo = pd.read_csv(WORK_ORDERS_CSV, sep=";", encoding="latin-1", low_memory=False)
    wo = wo[wo["customer_site_name"] == site].copy()
    wo["started"] = pd.to_datetime(wo["WORK_STARTED_DATETIME"], dayfirst=True, errors="coerce", utc=True)
    wo_recent = wo[wo["started"] >= wo["started"].max() - pd.Timedelta(days=365)]

    wo_summary = {
        "total_all_time": int(len(wo)),
        "last_12_months": int(len(wo_recent)),
        "on_demand": int((wo_recent["WORK_ORDER_TYPE_ENG"] == "On-demand work").sum()),
        "scheduled_pm": int(
            wo_recent["WORK_ORDER_TYPE_ENG"].astype(str).str.contains("Periodic", case=False, na=False).sum()
        ),
        "sla_violations": int(wo_recent["IS_SLA_VIOLATION"].fillna(0).astype(float).sum()),
    }

    repeat_topics = Counter()
    for desc in wo_recent["WORK_ORDER_DESCRIPTION"].dropna().astype(str):
        token = desc.split(",")[0].strip()[:80]
        if token:
            repeat_topics[token] += 1

    repeat_issues = [
        {"topic": topic, "count": count}
        for topic, count in repeat_topics.most_common(8)
        if count >= 2
    ]

    # Maintenance schedule
    pm = pd.read_csv(MAINTENANCE_CSV, encoding="utf-8-sig")
    pm = pm[pm["customer_site_name"] == site].copy()
    pm_active = pm[pm["OBJSTATE"].astype(str).str.lower() != "obsolete"]

    calendar_items = []
    for row in pm_active.head(40).itertuples():
        interval = ""
        if pd.notna(row.INTERVAL) and pd.notna(row.PM_INTERVAL_UNIT):
            interval = f"every {row.INTERVAL} {row.PM_INTERVAL_UNIT}"
        calendar_items.append(
            {
                "pm_no": int(row.PM_NO),
                "action": str(row.ACTION_DESCR_ENG or row.ACTION_DESCR)[:120],
                "description": str(row.DESCRIPTION_ENG or row.DESCRIPTION)[:200],
                "interval": interval or "calendar-based",
                "plan_hours": float(row.PLAN_HRS) if pd.notna(row.PLAN_HRS) else None,
                "state": str(row.OBJSTATE),
            }
        )

    return {
        "building_id": "lentokentankatu_11",
        "meta": BUILDINGS["lentokentankatu_11"],
        "alarm_weekly": weekly_list,
        "recent_alarms": alarm_records,
        "alarm_type_counts": dict(type_counts.most_common(10)),
        "alarm_location_counts": dict(location_counts.most_common(10)),
        "work_orders": wo_summary,
        "repeat_issues": repeat_issues,
        "maintenance_calendar": calendar_items,
    }


def process_aurora_house() -> dict[str, Any]:
    with open(AURORA_SMARTTI, encoding="utf-8") as f:
        raw = json.load(f)

    prop = raw["property"]
    nodes = {n["id"]: n["name"] for n in prop.get("nodes", [])}

    # Sample climate readings — last 60 days, daily averages per sensor key
    climate_series: dict[str, list[dict]] = defaultdict(list)
    cutoff = datetime.now(timezone.utc) - timedelta(days=60)

    for metric in ("interior_co2_ppm", "interior_temperature_C"):
        block = prop.get("readings", {}).get(metric, {})
        data = block.get("data", [])
        daily: dict[tuple[str, str], list[float]] = defaultdict(list)
        for point in data:
            t = _parse_dt(point.get("t"))
            if not t or t < cutoff:
                continue
            key = point.get("key", "unknown")
            day = t.strftime("%Y-%m-%d")
            daily[(key, day)].append(float(point["v"]))

        for (key, day), values in sorted(daily.items()):
            climate_series[metric].append(
                {
                    "day": day,
                    "sensor_key": key,
                    "node_name": nodes.get(key.split("/")[0], key),
                    "avg": round(sum(values) / len(values), 2),
                    "max": round(max(values), 2),
                    "samples": len(values),
                }
            )

    # Incidents
    incidents = []
    for inc in prop.get("incidents", []):
        created = _parse_dt(inc.get("created_at"))
        if not created:
            continue
        incidents.append(
            {
                "id": inc["id"],
                "time": created.isoformat(),
                "event_type": inc.get("event_type", ""),
                "category": inc.get("category", ""),
                "priority": inc.get("priority", ""),
                "status": inc.get("status", ""),
                "description": (inc.get("description") or "")[:300],
                "node_name": nodes.get(inc.get("node_id"), "Building"),
            }
        )

    incidents.sort(key=lambda x: x["time"], reverse=True)

    fault_incidents = [i for i in incidents if i["category"] == "fault"]
    condition_incidents = [i for i in incidents if i["category"] == "conditions_deviation"]

    return {
        "building_id": "aurora_house",
        "meta": BUILDINGS["aurora_house"],
        "climate_daily": dict(climate_series),
        "incidents_total": len(incidents),
        "incidents_fault": len(fault_incidents),
        "recent_incidents": incidents[:80],
        "fault_incidents": fault_incidents[:30],
        "condition_incidents": condition_incidents[:20],
    }


def build_all() -> None:
    _ensure_data_dir()
    datasets = {
        "lentokentankatu_11": process_lentokentankatu(),
        "aurora_house": process_aurora_house(),
    }
    for building_id, payload in datasets.items():
        out = DATA_DIR / f"{building_id}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"Wrote {out} ({out.stat().st_size // 1024} KB)")

    index = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "buildings": [
            {"id": bid, **BUILDINGS[bid]} for bid in datasets
        ],
    }
    with open(DATA_DIR / "index.json", "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print("Done.")


if __name__ == "__main__":
    build_all()
