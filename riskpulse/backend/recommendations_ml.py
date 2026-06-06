"""ML-flavoured recommendations — extends rule-based actions with model outputs."""

from __future__ import annotations

from typing import Any

from recommendations import generate_recommendations


def generate_recommendations_ml(data: dict[str, Any], analysis: dict[str, Any]) -> list[dict[str, Any]]:
    base = generate_recommendations(data, analysis)
    ml = analysis.get("ml") or {}
    if not ml.get("anomaly", {}).get("available") and not ml.get("forecast", {}).get("available"):
        return base

    fail_pct = int(ml.get("failure_probability_7d", 0) * 100)
    forecast = ml.get("forecast", {})
    anomaly = ml.get("anomaly", {})

    ml_actions: list[dict[str, Any]] = []

    if anomaly.get("is_anomaly"):
        ml_actions.append(
            {
                "id": "ml_preemptive_dispatch",
                "priority": "P1 — Immediate" if fail_pct >= 60 else "P2 — This week",
                "role": "manager",
                "title": "ML-preemptive dispatch (before fault report)",
                "reason": f"Isolation Forest anomaly + {fail_pct}% 7-day escalation risk — {anomaly.get('detail', '')}",
                "steps": [
                    "Treat ML alert equal to a Priority-2 alarm until cleared",
                    "Assign technician to highest-correlation zone from recent signals",
                    "Re-check model score in 48h; close loop in work order",
                    "Log outcome to improve future model training",
                ],
                "impact": "Intervene during anomaly window — typical lead time before occupant-visible failure",
                "vs_reactive": "Today: wait for alarm. ML: act when pattern deviates from learned normal.",
            }
        )

    if forecast.get("available") and forecast.get("trend") == "rising":
        ml_actions.append(
            {
                "id": "ml_capacity_plan",
                "priority": "P2 — This week",
                "role": "manager",
                "title": f"Staff for forecast spike ({forecast.get('predicted_value')} {forecast.get('horizon', '')})",
                "reason": f"Linear trend model predicts {forecast['trend']} load vs recent mean {forecast.get('recent_mean')}",
                "steps": [
                    "Hold 1 technician slot open on predicted peak day",
                    "Pre-stage parts for dominant alarm/incident category",
                    "Defer non-correlated calendar PM if forecast confidence high",
                ],
                "impact": "Capacity matches predicted load — avoids SLA breach during spikes",
                "vs_reactive": "Calendar staffing vs demand-driven staffing from forecast.",
            }
        )

    ml_actions.append(
        {
            "id": "ml_owner_brief",
            "priority": "P3 — Schedule",
            "role": "owner",
            "title": "ML reliability brief for portfolio report",
            "reason": ml.get("failure_label", f"Model-estimated risk {fail_pct}%"),
            "steps": [
                "Include ML escalation probability alongside reliability index",
                "Note models used: " + ", ".join(ml.get("models_used", [])),
                "Compare ML vs rule-based score — highlight early warning value",
            ],
            "impact": "Investor narrative: predictive capability backed by trained models",
            "vs_reactive": "Backward-looking reports vs forward-looking model outputs.",
        }
    )

    if data.get("profile") == "smartti" and anomaly.get("is_anomaly"):
        ml_actions.append(
            {
                "id": "ml_ventilation_tech",
                "priority": "P1 — Immediate",
                "role": "technician",
                "title": "ML-triggered ventilation check (CO₂ model)",
                "reason": ml.get("multivariate", {}).get("detail", anomaly.get("detail", "")),
                "steps": [
                    "Inspect zones with highest recent CO₂ spread (mean vs max delta)",
                    "Verify damper schedules — ML flagged abnormal multi-sensor pattern",
                    "Confirm correction: daily CO₂ returns inside learned normal band",
                ],
                "impact": "Prevent comfort complaints before Smartti fault incident",
                "vs_reactive": "Fix when model flags drift, not when tenant calls.",
            }
        )

    # ML actions first, then base (dedupe by id)
    seen = {a["id"] for a in ml_actions}
    merged = ml_actions + [a for a in base if a["id"] not in seen]
    return merged[:6]
