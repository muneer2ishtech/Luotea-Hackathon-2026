"""ML-enhanced risk scoring: anomaly detection + short-horizon forecast."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression

from risk_engine import _risk_label, _risk_level, analyze_building


def _sigmoid(x: float) -> float:
    return float(1.0 / (1.0 + np.exp(-x)))


def _anomaly_features(series: list[float]) -> np.ndarray:
    """Lag + rolling features for each point in a univariate series."""
    arr = np.array(series, dtype=float)
    n = len(arr)
    rows = []
    for i in range(n):
        lag1 = arr[i - 1] if i >= 1 else arr[i]
        lag2 = arr[i - 2] if i >= 2 else lag1
        window = arr[max(0, i - 3) : i + 1]
        roll = float(np.mean(window))
        delta = float(arr[i] - lag1) if i >= 1 else 0.0
        rows.append([arr[i], lag1, lag2, roll, delta])
    return np.array(rows)


def _run_isolation_forest(series: list[float]) -> dict[str, Any]:
    if len(series) < 8:
        return {
            "available": False,
            "reason": "Need at least 8 historical points to train",
        }

    X = _anomaly_features(series)
    train, probe = X[:-1], X[-1:]
    model = IsolationForest(contamination=0.12, random_state=42, n_estimators=100)
    model.fit(train)
    score = float(model.decision_function(probe)[0])
    prediction = int(model.predict(probe)[0])  # -1 anomaly, 1 normal
    is_anomaly = prediction == -1

    # Map decision_function (~[-0.5, 0.5]) to 0–100 risk contribution
    anomaly_risk = round(max(0, min(100, (0.25 - score) * 120)), 1)

    return {
        "available": True,
        "model": "IsolationForest",
        "is_anomaly": is_anomaly,
        "anomaly_score": round(score, 3),
        "anomaly_risk": anomaly_risk,
        "detail": (
            "ML flagged current period as an anomaly — pattern differs from learned normal weeks"
            if is_anomaly
            else "ML: current period matches learned normal operational pattern"
        ),
    }


def _forecast_next(values: list[float], horizon_label: str = "next period") -> dict[str, Any]:
    if len(values) < 6:
        return {"available": False, "reason": "Insufficient history for forecast"}

    y = np.array(values, dtype=float)
    X = np.arange(len(y)).reshape(-1, 1)
    reg = LinearRegression()
    reg.fit(X, y)
    next_x = np.array([[len(y)]])
    predicted = float(reg.predict(next_x)[0])
    predicted = max(0.0, predicted)

    recent_mean = float(np.mean(y[-4:]))
    slope = float(reg.coef_[0])
    trend = "rising" if slope > 0.05 else "falling" if slope < -0.05 else "stable"

    return {
        "available": True,
        "model": "LinearRegression",
        "horizon": horizon_label,
        "predicted_value": round(predicted, 1),
        "recent_mean": round(recent_mean, 1),
        "trend": trend,
        "slope": round(slope, 3),
    }


def _failure_probability(anomaly: dict[str, Any], forecast: dict[str, Any], stats_score: float) -> float:
    parts = [stats_score / 100.0]
    if anomaly.get("available") and anomaly.get("is_anomaly"):
        parts.append(0.35)
    if forecast.get("available") and forecast.get("trend") == "rising":
        pred = forecast.get("predicted_value", 0)
        recent = forecast.get("recent_mean", 1) or 1
        if pred > recent * 1.2:
            parts.append(0.25)
    return round(min(0.95, _sigmoid(2.2 * (max(parts) - 0.35)) * max(parts)), 2)


def analyze_alarm_site_ml(data: dict[str, Any], stats: dict[str, Any]) -> dict[str, Any]:
    weekly = data.get("alarm_weekly", [])
    counts = [w["count"] for w in weekly]
    if not counts:
        return stats

    anomaly = _run_isolation_forest(counts)
    forecast = _forecast_next(counts, "next week (alarms)")

    fail_prob = _failure_probability(anomaly, forecast, stats.get("score", 0))

    ml_score = stats.get("score", 0)
    if anomaly.get("available"):
        ml_score = min(100, 0.45 * stats.get("score", 0) + 0.55 * anomaly.get("anomaly_risk", 0))
    if fail_prob >= 0.6:
        ml_score = min(100, ml_score + 15)

    level = _risk_level(ml_score)
    signals = list(stats.get("signals", []))
    signals.insert(
        0,
        {
            "id": "ml_anomaly",
            "title": "ML anomaly detection (Isolation Forest)",
            "detail": anomaly.get("detail", anomaly.get("reason", "")),
            "severity": "high" if anomaly.get("is_anomaly") else "low",
            "metric": "ml_anomaly",
            "current": anomaly.get("anomaly_score"),
            "baseline": None,
        },
    )
    if forecast.get("available"):
        signals.insert(
            1,
            {
                "id": "ml_forecast",
                "title": f"Forecast: {forecast['predicted_value']} alarms {forecast['horizon']}",
                "detail": f"Trend {forecast['trend']} (slope {forecast['slope']}/week) — model trained on {len(counts)} weeks",
                "severity": "high" if forecast["trend"] == "rising" and forecast["predicted_value"] > forecast["recent_mean"] * 1.3 else "medium" if forecast["trend"] == "rising" else "low",
                "metric": "ml_forecast",
                "current": forecast["predicted_value"],
                "baseline": forecast["recent_mean"],
            },
        )

    chart = dict(stats.get("weekly_chart", {}))
    if forecast.get("available") and chart.get("weeks"):
        chart["forecast_point"] = {
            "label": "ML forecast",
            "value": forecast["predicted_value"],
        }

    stats.update(
        {
            "score": round(ml_score, 1),
            "level": level,
            "label": _risk_label(level),
            "signals": signals,
            "weekly_chart": chart,
            "method": "ml",
            "ml": {
                "anomaly": anomaly,
                "forecast": forecast,
                "failure_probability_7d": fail_prob,
                "failure_label": f"{int(fail_prob * 100)}% estimated escalation risk (7 days)",
                "models_used": ["IsolationForest", "LinearRegression"],
                "explainability": "Anomaly model learns multivariate weekly patterns (level, lag, rolling mean). Forecast extrapolates trend.",
            },
            "predictive_summary": {
                "headline": "Predictive mode (RiskPulse ML)",
                "points": [
                    f"ML risk score {round(ml_score)} — {_risk_label(level).lower()}",
                    f"Failure/escalation probability (7d): {int(fail_prob * 100)}%",
                    anomaly.get("detail", "Anomaly model active"),
                    f"Forecast {forecast.get('predicted_value', '—')} alarms next week ({forecast.get('trend', '—')} trend)",
                ],
            },
        }
    )
    return stats


def analyze_climate_site_ml(data: dict[str, Any], stats: dict[str, Any]) -> dict[str, Any]:
    co2 = data.get("climate_daily", {}).get("interior_co2_ppm", [])
    daily: dict[str, list[float]] = {}
    for row in co2:
        daily.setdefault(row["day"], []).append(row["avg"])
    days = sorted(daily.keys())
    values = [float(np.mean(daily[d])) for d in days]

    if len(values) < 8:
        stats["method"] = "ml"
        stats["ml"] = {"available": False, "reason": "Insufficient daily CO₂ history"}
        return stats

    anomaly = _run_isolation_forest(values)
    forecast = _forecast_next(values, "next day (avg CO₂ ppm)")

    # Multi-sensor matrix: last 14 days × [mean, max, std] across sensors
    by_day_sensor: dict[str, list[float]] = {}
    for row in co2:
        by_day_sensor.setdefault(row["day"], []).append(row["avg"])
    recent_days = sorted(by_day_sensor.keys())[-14:]
    multi_rows = []
    for d in recent_days:
        vals = by_day_sensor[d]
        multi_rows.append([float(np.mean(vals)), float(np.max(vals)), float(np.std(vals) or 0)])
    multi_anomaly = {"available": False}
    if len(multi_rows) >= 8:
        Xm = np.array(multi_rows)
        mtrain, mprobe = Xm[:-1], Xm[-1:]
        mf = IsolationForest(contamination=0.15, random_state=7, n_estimators=80)
        mf.fit(mtrain)
        multi_anomaly = {
            "available": True,
            "model": "IsolationForest (multi-sensor CO₂)",
            "is_anomaly": int(mf.predict(mprobe)[0]) == -1,
            "anomaly_score": round(float(mf.decision_function(mprobe)[0]), 3),
            "detail": "Multivariate model on daily mean/max/spread across sensors",
        }

    fail_prob = _failure_probability(anomaly, forecast, stats.get("score", 0))
    if multi_anomaly.get("available") and multi_anomaly.get("is_anomaly"):
        fail_prob = min(0.95, fail_prob + 0.12)

    ml_score = stats.get("score", 0)
    if anomaly.get("available"):
        ml_score = min(100, 0.4 * stats.get("score", 0) + 0.6 * anomaly.get("anomaly_risk", 0))

    level = _risk_level(ml_score)
    signals = list(stats.get("signals", []))
    signals.insert(
        0,
        {
            "id": "ml_co2_anomaly",
            "title": "ML CO₂ pattern anomaly",
            "detail": anomaly.get("detail", ""),
            "severity": "high" if anomaly.get("is_anomaly") else "low",
            "metric": "ml_anomaly",
            "current": anomaly.get("anomaly_score"),
            "baseline": None,
        },
    )
    if multi_anomaly.get("available"):
        signals.insert(
            1,
            {
                "id": "ml_multivariate",
                "title": "Multi-sensor ML alert",
                "detail": multi_anomaly["detail"] + (" — ANOMALY" if multi_anomaly.get("is_anomaly") else " — normal"),
                "severity": "high" if multi_anomaly.get("is_anomaly") else "low",
                "metric": "ml_multivariate",
                "current": multi_anomaly.get("anomaly_score"),
                "baseline": None,
            },
        )

    chart = dict(stats.get("weekly_chart", {}))
    if forecast.get("available"):
        chart["forecast_point"] = {"label": "ML forecast", "value": forecast["predicted_value"]}

    stats.update(
        {
            "score": round(ml_score, 1),
            "level": level,
            "label": _risk_label(level),
            "signals": signals,
            "weekly_chart": chart,
            "method": "ml",
            "ml": {
                "anomaly": anomaly,
                "multivariate": multi_anomaly,
                "forecast": forecast,
                "failure_probability_7d": fail_prob,
                "failure_label": f"{int(fail_prob * 100)}% comfort/fault incident risk (7 days)",
                "models_used": ["IsolationForest", "IsolationForest (multi-sensor)", "LinearRegression"],
                "explainability": "Models learn normal CO₂ dynamics; anomalies precede occupant complaints in historical data.",
            },
            "predictive_summary": {
                "headline": "Predictive mode (RiskPulse ML)",
                "points": [
                    f"ML risk score {round(ml_score)} — {_risk_label(level).lower()}",
                    f"Incident probability (7d): {int(fail_prob * 100)}%",
                    (
                        f"Forecast CO₂ {forecast['predicted_value']} ppm ({forecast['trend']})"
                        if forecast.get("available")
                        else "Forecast pending"
                    ),
                    "Ventilation intervention recommended before fault reports",
                ],
            },
        }
    )
    return stats


def analyze_building_ml(data: dict[str, Any]) -> dict[str, Any]:
    stats = analyze_building(data)
    stats["method"] = "stats"
    building_id = data.get("building_id", "")
    if building_id == "lentokentankatu_11":
        result = analyze_alarm_site_ml(data, stats)
    else:
        result = analyze_climate_site_ml(data, stats)
    result["building_id"] = building_id
    result["meta"] = data.get("meta", {})
    result["computed_at"] = datetime.now(timezone.utc).isoformat()
    return result
