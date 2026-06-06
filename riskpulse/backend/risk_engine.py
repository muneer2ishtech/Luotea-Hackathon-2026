"""Risk scoring: normal variation vs elevated risk (no ML — statistics + rules)."""

from __future__ import annotations

import math
import statistics
from datetime import datetime, timezone
from typing import Any


def _z_score(value: float, history: list[float]) -> float:
    if len(history) < 3:
        return 0.0
    mean = statistics.mean(history)
    stdev = statistics.stdev(history)
    if stdev == 0:
        return 0.0
    return (value - mean) / stdev


def _risk_level(score: float) -> str:
    if score >= 70:
        return "critical"
    if score >= 45:
        return "elevated"
    if score >= 25:
        return "watch"
    return "normal"


def _risk_label(level: str) -> str:
    return {
        "critical": "Elevated risk — act now",
        "elevated": "Above normal — investigate",
        "watch": "Watch zone",
        "normal": "Normal variation",
    }[level]


def analyze_alarm_site(data: dict[str, Any]) -> dict[str, Any]:
    weekly = data.get("alarm_weekly", [])
    counts = [w["count"] for w in weekly]
    if not counts:
        return {"score": 0, "level": "normal", "signals": []}

    # Baseline: all weeks except the most recent 2
    history = counts[:-2] if len(counts) > 2 else counts
    recent = counts[-1] if counts else 0
    prev = counts[-2] if len(counts) > 1 else recent

    baseline_median = statistics.median(history) if history else recent
    baseline_mean = statistics.mean(history) if history else recent
    z = _z_score(recent, history)

    # Composite score 0–100
    spike_ratio = recent / baseline_median if baseline_median > 0 else 1.0
    trend = (recent - prev) / prev if prev > 0 else 0.0
    score = min(
        100,
        max(
            0,
            20 * max(0, z)
            + 25 * max(0, spike_ratio - 1)
            + 15 * max(0, trend)
            + 10 * min(data.get("work_orders", {}).get("sla_violations", 0), 5),
        ),
    )
    level = _risk_level(score)

    signals = []
    if z >= 1.5 or spike_ratio >= 2:
        signals.append(
            {
                "id": "alarm_spike",
                "title": "Alarm frequency spike",
                "detail": f"This week: {recent} alarms vs baseline median {baseline_median:.0f}/week (z={z:.1f})",
                "severity": "high" if z >= 2 else "medium",
                "metric": "alarms_per_week",
                "current": recent,
                "baseline": round(baseline_median, 1),
            }
        )
    else:
        signals.append(
            {
                "id": "alarm_normal",
                "title": "Alarm rate within normal band",
                "detail": f"This week: {recent} alarms (baseline ~{baseline_median:.0f}/week)",
                "severity": "low",
                "metric": "alarms_per_week",
                "current": recent,
                "baseline": round(baseline_median, 1),
            }
        )

    top_types = data.get("alarm_type_counts", {})
    if top_types:
        dominant = max(top_types, key=top_types.get)
        signals.append(
            {
                "id": "alarm_dominant_type",
                "title": f"Dominant alarm category: {dominant}",
                "detail": f"{top_types[dominant]} events in last 90 days — pattern worth targeted inspection",
                "severity": "medium" if top_types[dominant] > 20 else "low",
                "metric": "alert_type",
                "current": top_types[dominant],
                "baseline": None,
            }
        )

    repeat = data.get("repeat_issues", [])
    if repeat and repeat[0]["count"] >= 3:
        signals.append(
            {
                "id": "repeat_work_orders",
                "title": "Recurring work order theme",
                "detail": f"\"{repeat[0]['topic']}\" appeared {repeat[0]['count']} times in 12 months",
                "severity": "medium",
                "metric": "repeat_issues",
                "current": repeat[0]["count"],
                "baseline": 1,
            }
        )

    return {
        "score": round(score, 1),
        "level": level,
        "label": _risk_label(level),
        "signals": signals,
        "weekly_chart": {
            "weeks": [w["week_start"] for w in weekly[-26:]],
            "counts": [w["count"] for w in weekly[-26:]],
            "baseline_median": round(baseline_median, 1),
            "baseline_mean": round(baseline_mean, 1),
            "upper_band": round(baseline_mean + 2 * (statistics.stdev(history) if len(history) > 1 else 0), 1),
            "chart_type": "alarms",
            "chart_label": "Alarms per week",
        },
        "reactive_summary": {
            "headline": "Reactive mode (today)",
            "points": [
                f"{data.get('work_orders', {}).get('on_demand', 0)} on-demand work orders in last 12 months",
                f"{data.get('work_orders', {}).get('scheduled_pm', 0)} calendar-based PM visits",
                "Actions triggered after alarms or user fault reports",
                f"{len(data.get('recent_alarms', []))} alarms logged in last 90 days",
            ],
        },
        "predictive_summary": {
            "headline": "Predictive mode (with RiskPulse)",
            "points": [
                f"Risk score {round(score)} — {_risk_label(level).lower()}",
                "Weekly alarm trend compared to historical baseline",
                "Repeat-issue detection flags root causes before escalation",
                "Maintenance calendar adjusted by risk, not fixed dates alone",
            ],
        },
    }


def analyze_climate_site(data: dict[str, Any]) -> dict[str, Any]:
    co2 = data.get("climate_daily", {}).get("interior_co2_ppm", [])
    incident_weekly = data.get("incident_weekly", [])
    kone_weekly = data.get("kone_weekly", [])

    signals: list[dict[str, Any]] = []
    deviations: list[float] = []

    # Per sensor: compare last 7 days to prior 30
    by_sensor: dict[str, list[dict]] = {}
    for row in co2:
        by_sensor.setdefault(row["sensor_key"], []).append(row)

    for key, rows in by_sensor.items():
        rows.sort(key=lambda r: r["day"])
        if len(rows) < 10:
            continue
        history_vals = [r["avg"] for r in rows[:-7]]
        recent_vals = [r["avg"] for r in rows[-7:]]
        if not history_vals or not recent_vals:
            continue
        baseline = statistics.mean(history_vals)
        recent = statistics.mean(recent_vals)
        z = _z_score(recent, history_vals)
        if z >= 1.2 or recent > 1000:
            deviations.append(z)
            signals.append(
                {
                    "id": f"co2_{key}",
                    "title": f"CO₂ elevation — {rows[-1].get('node_name', key)}",
                    "detail": f"7-day avg {recent:.0f} ppm vs baseline {baseline:.0f} ppm (z={z:.1f})",
                    "severity": "high" if z >= 2 or recent > 1200 else "medium",
                    "metric": "interior_co2_ppm",
                    "current": round(recent, 1),
                    "baseline": round(baseline, 1),
                }
            )

    open_faults = [i for i in data.get("recent_incidents", []) if i.get("category") == "fault" and i.get("status") != "resolved"]
    if open_faults:
        signals.append(
            {
                "id": "open_faults",
                "title": f"{len(open_faults)} open fault incidents",
                "detail": open_faults[0].get("description", "")[:120],
                "severity": "high" if len(open_faults) >= 3 else "medium",
                "metric": "open_incidents",
                "current": len(open_faults),
                "baseline": 0,
            }
        )

    condition_count = len(data.get("condition_incidents", []))
    if condition_count >= 2:
        signals.append(
            {
                "id": "conditions_deviation",
                "title": "Indoor condition deviations logged",
                "detail": f"{condition_count} Smartti incidents tagged conditions_deviation",
                "severity": "medium",
                "metric": "conditions_incidents",
                "current": condition_count,
                "baseline": 0,
            }
        )

    # KONE occupancy load signal
    if kone_weekly and len(kone_weekly) >= 4:
        kone_counts = [w["count"] for w in kone_weekly]
        kone_recent = kone_counts[-1]
        kone_base = statistics.median(kone_counts[:-1]) if len(kone_counts) > 1 else kone_recent
        if kone_recent > kone_base * 1.4 and kone_recent >= 5:
            signals.append(
                {
                    "id": "kone_occupancy_peak",
                    "title": "High elevator/occupancy load (KONE)",
                    "detail": f"Recent peak index {kone_recent} vs baseline {kone_base:.1f} — stress on vertical transport",
                    "severity": "medium",
                    "metric": "kone_occupancy",
                    "current": kone_recent,
                    "baseline": round(kone_base, 1),
                }
            )

    if not signals:
        signals.append(
            {
                "id": "climate_normal",
                "title": "Climate sensors within normal band",
                "detail": "No significant CO₂ or temperature deviations in last 7 days",
                "severity": "low",
                "metric": "climate",
                "current": 0,
                "baseline": 0,
            }
        )

    score = min(
        100,
        max(0, 15 * len([s for s in signals if s["severity"] == "high"]) + 10 * len([s for s in signals if s["severity"] == "medium"]) + (max(deviations) * 12 if deviations else 0)),
    )
    level = _risk_level(score)

    # Build chart — prefer CO₂ daily; fall back to weekly incidents or KONE occupancy
    daily_co2: dict[str, list[float]] = {}
    for row in co2:
        daily_co2.setdefault(row["day"], []).append(row["avg"])
    days = sorted(daily_co2.keys())[-30:]

    if len(days) >= 7:
        chart_co2 = [round(statistics.mean(daily_co2[d]), 1) for d in days]
        co2_baseline = statistics.mean(chart_co2[:-7]) if len(chart_co2) > 7 else statistics.mean(chart_co2)
        weekly_chart = {
            "weeks": days,
            "counts": chart_co2,
            "baseline_median": round(co2_baseline, 1),
            "baseline_mean": round(co2_baseline, 1),
            "upper_band": round(co2_baseline + 150, 1),
            "chart_type": "co2",
            "chart_label": "Avg CO₂ (ppm) — last 30 days",
        }
    elif incident_weekly:
        inc_counts = [w["count"] for w in incident_weekly]
        inc_base = statistics.median(inc_counts) if inc_counts else 0
        weekly_chart = {
            "weeks": [w["week_start"] for w in incident_weekly],
            "counts": inc_counts,
            "baseline_median": round(inc_base, 1),
            "baseline_mean": round(statistics.mean(inc_counts) if inc_counts else 0, 1),
            "upper_band": round(inc_base * 2 + 1, 1),
            "chart_type": "incidents",
            "chart_label": "Smartti incidents per week",
        }
    elif kone_weekly:
        kc = [w["count"] for w in kone_weekly]
        kb = statistics.median(kc) if kc else 0
        weekly_chart = {
            "weeks": [w["week_start"] for w in kone_weekly],
            "counts": kc,
            "baseline_median": round(kb, 1),
            "baseline_mean": round(statistics.mean(kc) if kc else 0, 1),
            "upper_band": round(kb * 1.5 + 1, 1),
            "chart_type": "occupancy",
            "chart_label": "KONE occupancy index (weekly avg peak)",
        }
    else:
        weekly_chart = {
            "weeks": [],
            "counts": [],
            "baseline_median": 0,
            "baseline_mean": 0,
            "upper_band": 0,
            "chart_type": "co2",
            "chart_label": "No chart data",
        }

    return {
        "score": round(score, 1),
        "level": level,
        "label": _risk_label(level),
        "signals": signals,
        "weekly_chart": weekly_chart,
        "reactive_summary": {
            "headline": "Reactive mode (today)",
            "points": [
                f"{data.get('incidents_fault', 0)} fault incidents logged in Smartti",
                "Technicians respond after comfort complaints or fault reports",
                "Fixed HVAC inspection schedule regardless of sensor drift",
                "Energy/comfort issues discovered in monthly reports",
            ],
        },
        "predictive_summary": {
            "headline": "Predictive mode (with RiskPulse)",
            "points": [
                f"Risk score {round(score)} — {_risk_label(level).lower()}",
                "CO₂ trend compared to per-sensor baseline before complaints",
                "Open faults prioritized over routine calendar tasks",
                "Ventilation adjustments recommended when deviation detected",
            ],
        },
    }


def analyze_building(data: dict[str, Any]) -> dict[str, Any]:
    profile = data.get("profile", "smartti")
    if profile == "alarm":
        analysis = analyze_alarm_site(data)
    else:
        analysis = analyze_climate_site(data)

    analysis["building_id"] = data.get("building_id", "")
    analysis["meta"] = data.get("meta", {})
    analysis["method"] = "stats"
    analysis["computed_at"] = datetime.now(timezone.utc).isoformat()
    return analysis
