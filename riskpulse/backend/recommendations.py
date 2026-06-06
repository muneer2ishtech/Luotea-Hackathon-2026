"""Rule-based action recommendations from risk signals."""

from __future__ import annotations

from typing import Any


def _priority(severity: str, score: float) -> str:
    if severity == "high" or score >= 70:
        return "P1 — Immediate"
    if severity == "medium" or score >= 45:
        return "P2 — This week"
    return "P3 — Schedule"


def recommend_for_alarm_site(data: dict[str, Any], analysis: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    score = analysis.get("score", 0)
    signal_ids = {s["id"] for s in analysis.get("signals", [])}

    if "alarm_spike" in signal_ids:
        actions.append(
            {
                "id": "inspect_hvac_cluster",
                "priority": _priority("high", score),
                "role": "manager",
                "title": "Dispatch targeted HVAC inspection",
                "reason": "Alarm frequency exceeds normal band — investigate before next calendar PM",
                "steps": [
                    "Pull alarm cluster by location from last 7 days",
                    "Compare with upcoming scheduled maintenance (EH calendar)",
                    "If overlap > 60%, pull forward the PM visit by 2 weeks",
                    "Assign technician with alarm history context",
                ],
                "impact": "Prevents escalation from recurring small disturbances to major failure",
                "vs_reactive": "Today: wait for next fault report. Predictive: inspect while signal is elevated.",
            }
        )

    top_locs = data.get("alarm_location_counts", {})
    if top_locs:
        loc, count = next(iter(top_locs.items()))
        if count >= 5:
            actions.append(
                {
                    "id": "root_cause_location",
                    "priority": _priority("medium", score),
                    "role": "technician",
                    "title": f"Root-cause check at {loc}",
                    "reason": f"{count} alarms reference this location/equipment in 90 days",
                    "steps": [
                        f"Review last 5 alarms tagged '{loc}'",
                        "Check controller logs and sensor calibration",
                        "Verify whether issue is transient (return-to-normal) or drift",
                        "Document findings in work order — link alarm IDs",
                    ],
                    "impact": "Stops repeat alarm → dispatch → close → repeat cycle",
                    "vs_reactive": "Today: fix each alarm individually. Predictive: fix underlying cause once.",
                }
            )

    if "repeat_work_orders" in signal_ids:
        repeat = data.get("repeat_issues", [{}])[0]
        actions.append(
            {
                "id": "defer_low_risk_pm",
                "priority": _priority("medium", score),
                "role": "manager",
                "title": "Rebalance calendar: defer low-risk PM, accelerate hot spot",
                "reason": f"Repeat theme \"{repeat.get('topic', '')}\" suggests systemic issue",
                "steps": [
                    "Identify PM tasks with no recent alarm correlation",
                    "Defer 1–2 low-priority calendar items this month",
                    "Free capacity for repeat-issue investigation",
                    "Review with property owner at month-end",
                ],
                "impact": "Same budget hours, better outcome — risk-guided calendar",
                "vs_reactive": "Today: calendar runs regardless. Predictive: calendar flexes with risk.",
            }
        )

    sla = data.get("work_orders", {}).get("sla_violations", 0)
    if sla > 0:
        actions.append(
            {
                "id": "sla_recovery",
                "priority": "P2 — This week",
                "role": "owner",
                "title": "SLA recovery plan",
                "reason": f"{sla} SLA violations in last 12 months — reliability metric at risk",
                "steps": [
                    "Review violations tied to alarm response times",
                    "Set auto-escalation when weekly alarm z-score > 1.5",
                    "Report operational reliability index to owner monthly",
                ],
                "impact": "Shifts KPI from 'hours worked' to 'disruption prevented'",
                "vs_reactive": "Today: report violations after the fact. Predictive: escalate before breach.",
            }
        )

    if not actions:
        actions.append(
            {
                "id": "maintain_baseline",
                "priority": "P3 — Schedule",
                "role": "manager",
                "title": "Maintain baseline monitoring",
                "reason": "Signals within normal variation — keep calendar, watch trends",
                "steps": [
                    "Continue weekly alarm baseline comparison",
                    "No calendar changes recommended this week",
                ],
                "impact": "Avoids over-maintenance when risk is low",
                "vs_reactive": "Same as today, but with evidence-backed confidence.",
            }
        )

    return actions[:5]


def recommend_for_smartti_site(data: dict[str, Any], analysis: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    score = analysis.get("score", 0)

    for signal in analysis.get("signals", []):
        if signal["id"].startswith("co2_") and signal["severity"] in ("high", "medium"):
            actions.append(
                {
                    "id": f"ventilation_{signal['id']}",
                    "priority": _priority(signal["severity"], score),
                    "role": "technician",
                    "title": "Adjust ventilation before comfort complaints",
                    "reason": signal["detail"],
                    "steps": [
                        "Check damper positions and schedule overrides on affected zone",
                        "Verify CO₂ sensor calibration (compare adjacent sensors)",
                        "Increase fresh air temporarily; monitor 48h trend",
                        "If z-score remains > 2, create fault incident proactively",
                    ],
                    "impact": "Prevents 'Vikailmoitus' fault reports from occupants",
                    "vs_reactive": "Today: tenant complains → ticket. Predictive: fix when CO₂ drifts.",
                }
            )
            break

    open_faults = [i for i in data.get("recent_incidents", []) if i.get("category") == "fault" and i.get("status") != "resolved"]
    if open_faults:
        fault = open_faults[0]
        actions.append(
            {
                "id": "prioritize_open_fault",
                "priority": "P1 — Immediate",
                "role": "technician",
                "title": "Prioritize open fault over routine tasks",
                "reason": fault.get("description", "")[:150],
                "steps": [
                    "Move this fault above calendar-based filter changes",
                    "Assign technician with HVAC domain context",
                    "Close loop in Smartti incident when resolved",
                ],
                "impact": "Open faults are leading indicators — clearing them reduces future alarms",
                "vs_reactive": "Today: mixed queue by arrival time. Predictive: risk-ranked queue.",
            }
        )

    actions.append(
        {
            "id": "owner_esg_snapshot",
            "priority": "P3 — Schedule",
            "role": "owner",
            "title": "Weekly operational reliability snapshot",
            "reason": f"Building risk score {score}/100 — {analysis.get('label', '')}",
            "steps": [
                "Include CO₂ compliance trend and open fault count",
                "Compare energy/comfort incidents vs prior month",
                "Highlight any deferred vs accelerated maintenance decisions",
            ],
            "impact": "Owner sees outcomes (reliability), not just maintenance hours",
            "vs_reactive": "Today: monthly PDF report. Predictive: live risk + action log.",
        }
    )

    return actions[:5]


def generate_recommendations(data: dict[str, Any], analysis: dict[str, Any]) -> list[dict[str, Any]]:
    profile = data.get("profile", "smartti")
    if profile == "alarm":
        return recommend_for_alarm_site(data, analysis)
    return recommend_for_smartti_site(data, analysis)
