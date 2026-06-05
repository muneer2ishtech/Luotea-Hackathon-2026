"""Role-specific views: owner, manager, field technician — each with their own language."""

from __future__ import annotations

from typing import Any


ROLES = {
    "owner": {
        "label": "Owner / Investor",
        "tagline": "Value growth, returns, ESG reporting",
        "focus": "Portfolio-level visibility and comparability",
    },
    "manager": {
        "label": "Property Manager",
        "tagline": "Efficiency, situational awareness, cost control",
        "focus": "Real-time data to support decisions",
    },
    "technician": {
        "label": "Field Technician",
        "tagline": "Task prioritization, clear instructions, fast response",
        "focus": "Practical field guidelines",
    },
}


def _reliability_index(score: float) -> dict[str, str]:
    """Translate risk score into owner-friendly reliability language."""
    reliability = max(0, min(100, 100 - score))
    if reliability >= 80:
        grade, trend = "A", "stable"
    elif reliability >= 60:
        grade, trend = "B", "watch"
    elif reliability >= 40:
        grade, trend = "C", "declining"
    else:
        grade, trend = "D", "at risk"
    return {
        "index": round(reliability, 1),
        "grade": grade,
        "trend": trend,
        "label": f"Operational reliability {grade} ({reliability:.0f}/100)",
    }


def build_owner_view(
    data: dict[str, Any],
    analysis: dict[str, Any],
    recommendations: list[dict[str, Any]],
    portfolio: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    score = analysis.get("score", 0)
    rel = _reliability_index(score)
    meta = analysis.get("meta", {})
    wo = data.get("work_orders", {})

    owner_actions = [r for r in recommendations if r.get("role") == "owner"]
    if not owner_actions:
        owner_actions = [
            {
                "title": "Review operational reliability report",
                "reason": rel["label"],
                "steps": [
                    "Compare this asset to portfolio median",
                    "Assess impact on tenant satisfaction and asset value",
                    "Approve or defer recommended maintenance rebalancing",
                ],
            }
        ]

    esg_points = []
    if data.get("building_id") == "aurora_house":
        esg_points = [
            {"metric": "Indoor air (CO₂ trend)", "status": "watch" if score >= 25 else "on track", "note": "Sensor-based comfort before complaints"},
            {"metric": "Open fault incidents", "status": "action" if data.get("incidents_fault", 0) > 5 else "on track", "note": f"{data.get('incidents_fault', 0)} faults logged in Smartti"},
            {"metric": "Energy optimization actions", "status": "on track", "note": "Smartti incident log tracks optimization vs faults"},
        ]
    else:
        esg_points = [
            {"metric": "Disruption risk (alarms)", "status": "action" if score >= 45 else "on track", "note": f"Risk score {score:.0f}/100 — {analysis.get('label', '')}"},
            {"metric": "SLA compliance", "status": "action" if wo.get("sla_violations", 0) > 0 else "on track", "note": f"{wo.get('sla_violations', 0)} violations last 12 months"},
            {"metric": "Reactive vs planned work ratio", "status": "watch", "note": f"{wo.get('on_demand', 0)} on-demand vs {wo.get('scheduled_pm', 0)} scheduled PM (12 mo)"},
        ]

    portfolio_rows = portfolio or [
        {
            "id": data.get("building_id"),
            "name": meta.get("name", ""),
            "risk_score": score,
            "reliability_index": rel["index"],
            "grade": rel["grade"],
            "level": analysis.get("level", "normal"),
        }
    ]

    return {
        "role": "owner",
        "headline": f"{meta.get('name', 'Asset')} — portfolio snapshot",
        "subtitle": "Outcomes and comparability — not maintenance hours",
        "primary_metric": {
            "label": "Operational reliability index",
            "value": rel["index"],
            "unit": "/ 100",
            "grade": rel["grade"],
            "trend": rel["trend"],
            "explanation": "Higher is better. Derived from disruption risk across alarms, incidents, and SLA data.",
        },
        "kpis": [
            {"label": "Disruption risk", "value": f"{score:.0f}", "context": analysis.get("label", ""), "bad": score >= 45},
            {"label": "Asset", "value": meta.get("name", ""), "context": meta.get("address", ""), "bad": False},
            {"label": "Data sources", "value": str(len(meta.get("sources", []))), "context": ", ".join(meta.get("sources", [])), "bad": False},
        ],
        "esg_summary": esg_points,
        "portfolio": portfolio_rows,
        "decisions": [
            {
                "title": a["title"],
                "summary": a.get("reason", ""),
                "impact": a.get("impact", "Protects asset value and tenant experience"),
            }
            for a in owner_actions[:3]
        ],
        "language_hint": "Speak in returns, reliability, ESG — not alarm codes or PM numbers.",
    }


def build_manager_view(
    data: dict[str, Any],
    analysis: dict[str, Any],
    recommendations: list[dict[str, Any]],
) -> dict[str, Any]:
    score = analysis.get("score", 0)
    meta = analysis.get("meta", {})
    wo = data.get("work_orders", {})
    chart = analysis.get("weekly_chart", {})

    manager_actions = [r for r in recommendations if r.get("role") == "manager"]
    if not manager_actions:
        manager_actions = [r for r in recommendations if r.get("role") != "owner"][:3]

    calendar_hint = None
    if data.get("maintenance_calendar"):
        calendar_hint = {
            "scheduled_items": len(data["maintenance_calendar"]),
            "sample": [c["action"] for c in data["maintenance_calendar"][:3]],
            "recommendation": "Pull forward visits where alarm z-score > 1.5; defer low-correlation PM when risk is normal.",
        }

    efficiency = []
    if wo:
        total = wo.get("last_12_months", 1) or 1
        reactive_pct = round(100 * wo.get("on_demand", 0) / total, 1)
        efficiency = [
            {"label": "Work orders (12 mo)", "value": str(total)},
            {"label": "Reactive share", "value": f"{reactive_pct}%", "alert": reactive_pct > 60},
            {"label": "SLA violations", "value": str(wo.get("sla_violations", 0)), "alert": wo.get("sla_violations", 0) > 0},
        ]

    return {
        "role": "manager",
        "headline": f"{meta.get('name', 'Site')} — operations center",
        "subtitle": "Situational awareness and cost-smart scheduling",
        "risk_score": score,
        "risk_level": analysis.get("level", "normal"),
        "risk_label": analysis.get("label", ""),
        "signals": analysis.get("signals", []),
        "chart": chart,
        "efficiency": efficiency,
        "calendar": calendar_hint,
        "actions": manager_actions[:4],
        "situation_summary": _manager_situation(analysis, wo),
        "language_hint": "Speak in priorities, capacity, calendar trade-offs — what to do this week.",
    }


def _manager_situation(analysis: dict[str, Any], wo: dict[str, Any]) -> str:
    score = analysis.get("score", 0)
    if score >= 70:
        return "Elevated disruption risk — reallocate technician capacity from routine PM to targeted inspection."
    if score >= 45:
        return "Above-normal signals — review alarm clusters and consider pulling forward one maintenance visit."
    if wo.get("sla_violations", 0) > 0:
        return "Risk normal but SLA history shows gaps — tighten escalation rules on alarm spikes."
    return "Within normal variation — maintain calendar, continue baseline monitoring."


def build_technician_view(
    data: dict[str, Any],
    analysis: dict[str, Any],
    recommendations: list[dict[str, Any]],
) -> dict[str, Any]:
    meta = analysis.get("meta", {})
    score = analysis.get("score", 0)

    tech_actions = [r for r in recommendations if r.get("role") == "technician"]
    # Fall back to any non-owner action as field work
    if not tech_actions:
        tech_actions = [r for r in recommendations if r.get("role") != "owner"]

    tasks = []
    for i, action in enumerate(tech_actions[:5], start=1):
        tasks.append(
            {
                "rank": i,
                "priority": action.get("priority", "P2 — This week"),
                "title": action["title"],
                "location": _task_location(data, action),
                "why_now": action.get("reason", ""),
                "checklist": action.get("steps", []),
                "done_when": action.get("impact", "Issue resolved and logged in work order"),
            }
        )

    # Add concrete alarm/incident as top task context when available
    field_context = []
    if data.get("recent_alarms"):
        alarm = data["recent_alarms"][0]
        field_context.append(
            {
                "type": "alarm",
                "time": alarm.get("time", "")[:10],
                "text": alarm.get("description", "")[:200],
                "location": alarm.get("location_hint", ""),
            }
        )
    if data.get("recent_incidents"):
        inc = next((i for i in data["recent_incidents"] if i.get("category") == "fault"), None)
        if inc:
            field_context.append(
                {
                    "type": "incident",
                    "time": inc.get("time", "")[:10],
                    "text": inc.get("description", "")[:200],
                    "location": inc.get("node_name", "Building"),
                }
            )

    return {
        "role": "technician",
        "headline": "Today's task queue",
        "subtitle": f"{meta.get('name', 'Site')} — risk-ranked, newest critical work first",
        "task_count": len(tasks),
        "risk_context": f"Site risk {score:.0f}/100 — prioritize tasks marked P1",
        "tasks": tasks,
        "field_context": field_context,
        "language_hint": "Short sentences, locations, checklists — no portfolio or ESG jargon.",
    }


def _task_location(data: dict[str, Any], action: dict[str, Any]) -> str:
    title = action.get("title", "")
    if " at " in title:
        return title.split(" at ", 1)[1]
    if data.get("recent_alarms"):
        return data["recent_alarms"][0].get("location_hint", "See work order")
    return data.get("meta", {}).get("address", "On site")


def build_all_audiences(
    data: dict[str, Any],
    analysis: dict[str, Any],
    recommendations: list[dict[str, Any]],
    portfolio: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "roles": ROLES,
        "owner": build_owner_view(data, analysis, recommendations, portfolio),
        "manager": build_manager_view(data, analysis, recommendations),
        "technician": build_technician_view(data, analysis, recommendations),
    }


def build_portfolio_summary(all_analyses: list[tuple[dict, dict]]) -> list[dict[str, Any]]:
    """Cross-building rows for owner portfolio view."""
    rows = []
    for data, analysis in all_analyses:
        score = analysis.get("score", 0)
        rel = _reliability_index(score)
        rows.append(
            {
                "id": data.get("building_id"),
                "name": data.get("meta", {}).get("name", ""),
                "customer": data.get("meta", {}).get("customer", ""),
                "risk_score": round(score, 1),
                "reliability_index": rel["index"],
                "grade": rel["grade"],
                "level": analysis.get("level", "normal"),
                "label": analysis.get("label", ""),
            }
        )
    rows.sort(key=lambda r: r["risk_score"], reverse=True)
    return rows
