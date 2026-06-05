"""FastAPI server for RiskPulse demo."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from audiences import build_all_audiences, build_portfolio_summary
from config import BUILDINGS, DATA_DIR
from recommendations import generate_recommendations
from risk_engine import analyze_building

app = FastAPI(
    title="RiskPulse",
    description="Luotea Hackathon 2026 — reactive to predictive maintenance demo",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"
_cache: dict[str, dict] = {}


def _load_building(building_id: str) -> dict:
    if building_id in _cache:
        return _cache[building_id]
    path = DATA_DIR / f"{building_id}.json"
    if not path.exists():
        raise HTTPException(
            status_code=503,
            detail=f"Processed data missing for {building_id}. Run: python preprocess.py",
        )
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    _cache[building_id] = data
    return data


@app.get("/api/health")
def health():
    ready = (DATA_DIR / "index.json").exists()
    return {"status": "ok" if ready else "needs_preprocess", "data_dir": str(DATA_DIR)}


@app.get("/api/buildings")
def list_buildings():
    index_path = DATA_DIR / "index.json"
    if index_path.exists():
        with open(index_path, encoding="utf-8") as f:
            return json.load(f)
    return {
        "buildings": [{"id": k, **v} for k, v in BUILDINGS.items()],
    }


@app.get("/api/portfolio")
def get_portfolio():
    """Owner view: all buildings compared on one screen."""
    pairs: list[tuple[dict, dict]] = []
    for building_id in BUILDINGS:
        data = _load_building(building_id)
        analysis = analyze_building(data)
        pairs.append((data, analysis))
    portfolio = build_portfolio_summary(pairs)
    avg_reliability = round(
        sum(r["reliability_index"] for r in portfolio) / len(portfolio), 1
    ) if portfolio else 0
    return {
        "portfolio": portfolio,
        "summary": {
            "asset_count": len(portfolio),
            "avg_reliability_index": avg_reliability,
            "highest_risk": portfolio[0] if portfolio else None,
            "lowest_risk": portfolio[-1] if portfolio else None,
        },
    }


@app.get("/api/buildings/{building_id}/analysis")
def get_analysis(building_id: str):
    if building_id not in BUILDINGS:
        raise HTTPException(404, "Unknown building")
    data = _load_building(building_id)
    analysis = analyze_building(data)
    actions = generate_recommendations(data, analysis)

    # Portfolio context for owner comparability
    portfolio_pairs = []
    for bid in BUILDINGS:
        d = _load_building(bid)
        portfolio_pairs.append((d, analyze_building(d)))
    portfolio = build_portfolio_summary(portfolio_pairs)

    audiences = build_all_audiences(data, analysis, actions, portfolio)

    return {
        "analysis": analysis,
        "recommendations": actions,
        "audiences": audiences,
        "raw_summary": {
            "work_orders": data.get("work_orders"),
            "incidents_total": data.get("incidents_total"),
            "alarm_types": data.get("alarm_type_counts"),
        },
    }


@app.get("/api/buildings/{building_id}/chart")
def get_chart(building_id: str):
    if building_id not in BUILDINGS:
        raise HTTPException(404, "Unknown building")
    data = _load_building(building_id)
    analysis = analyze_building(data)
    return analysis.get("weekly_chart", {})


@app.get("/")
def serve_index():
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
