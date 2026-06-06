"""FastAPI server for RiskPulse demo."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from audiences import build_all_audiences, build_portfolio_summary
from config import BUILDINGS, DATA_DIR
from recommendations import generate_recommendations
from recommendations_ml import generate_recommendations_ml
from risk_engine import analyze_building
from risk_engine_ml import analyze_building_ml

app = FastAPI(
    title="RiskPulse",
    description="Luotea Hackathon 2026 — reactive to predictive maintenance demo",
    version="0.2.1",
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


def _available_buildings() -> list[dict]:
    """Buildings registered in config with processed JSON on disk."""
    out = []
    for bid, cfg in BUILDINGS.items():
        if (DATA_DIR / f"{bid}.json").exists():
            out.append({"id": bid, **cfg})
    return out


def _ensure_building_id(building_id: str) -> None:
    if building_id not in BUILDINGS:
        raise HTTPException(404, detail=f"Unknown building: {building_id}")
    if not (DATA_DIR / f"{building_id}.json").exists():
        raise HTTPException(
            503,
            detail=f"No processed data for {building_id}. Run: python preprocess.py",
        )


def _portfolio_for(analyze_fn: Callable[[dict], dict]) -> list[dict]:
    pairs: list[tuple[dict, dict]] = []
    for building_id in BUILDINGS:
        if not (DATA_DIR / f"{building_id}.json").exists():
            continue
        data = _load_building(building_id)
        pairs.append((data, analyze_fn(data)))
    return build_portfolio_summary(pairs)


def _analysis_payload(
    building_id: str,
    analyze_fn: Callable[[dict], dict],
    recommend_fn: Callable,
) -> dict:
    _ensure_building_id(building_id)
    data = _load_building(building_id)
    analysis = analyze_fn(data)
    actions = recommend_fn(data, analysis)
    portfolio = _portfolio_for(analyze_fn)
    audiences = build_all_audiences(data, analysis, actions, portfolio)
    return {
        "mode": analysis.get("method", "stats"),
        "analysis": analysis,
        "recommendations": actions,
        "audiences": audiences,
        "raw_summary": {
            "work_orders": data.get("work_orders"),
            "incidents_total": data.get("incidents_total"),
            "alarm_types": data.get("alarm_type_counts"),
        },
    }


def _register_mode_routes(
    router: APIRouter,
    analyze_fn: Callable[[dict], dict],
    recommend_fn: Callable,
) -> None:
    @router.get("/buildings")
    def list_buildings():
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "buildings": _available_buildings(),
            "mode": "ml" if analyze_fn is analyze_building_ml else "stats",
            "building_count": len(BUILDINGS),
        }

    @router.get("/portfolio")
    def get_portfolio():
        portfolio = _portfolio_for(analyze_fn)
        avg_reliability = round(
            sum(r["reliability_index"] for r in portfolio) / len(portfolio), 1
        ) if portfolio else 0
        return {
            "mode": "ml" if analyze_fn is analyze_building_ml else "stats",
            "portfolio": portfolio,
            "summary": {
                "asset_count": len(portfolio),
                "avg_reliability_index": avg_reliability,
                "highest_risk": portfolio[0] if portfolio else None,
                "lowest_risk": portfolio[-1] if portfolio else None,
            },
        }

    @router.get("/buildings/{building_id}/analysis")
    def get_analysis(building_id: str):
        return _analysis_payload(building_id, analyze_fn, recommend_fn)

    @router.get("/buildings/{building_id}/chart")
    def get_chart(building_id: str):
        _ensure_building_id(building_id)
        data = _load_building(building_id)
        analysis = analyze_fn(data)
        return analysis.get("weekly_chart", {})


no_ml_router = APIRouter(prefix="/api/riskpulse-no-ml", tags=["no-ml"])
ml_router = APIRouter(prefix="/api/riskpulse-ml", tags=["ml"])
_register_mode_routes(no_ml_router, analyze_building, generate_recommendations)
_register_mode_routes(ml_router, analyze_building_ml, generate_recommendations_ml)
app.include_router(no_ml_router)
app.include_router(ml_router)


@app.on_event("startup")
def startup_log():
    available = _available_buildings()
    print(f"RiskPulse: {len(BUILDINGS)} configured, {len(available)} with processed data")


@app.get("/api/health")
def health():
    available = _available_buildings()
    return {
        "status": "ok" if available else "needs_preprocess",
        "data_dir": str(DATA_DIR),
        "configured_buildings": len(BUILDINGS),
        "available_buildings": len(available),
        "building_ids": [b["id"] for b in available],
    }


@app.get("/")
def root():
    return RedirectResponse(url="/riskpulse-no-ml")


@app.get("/riskpulse-no-ml")
def page_no_ml():
    return FileResponse(FRONTEND_DIR / "riskpulse-no-ml.html")


@app.get("/riskpulse-ml")
def page_ml():
    return FileResponse(FRONTEND_DIR / "riskpulse-ml.html")


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
