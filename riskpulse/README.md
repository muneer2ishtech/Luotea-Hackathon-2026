# RiskPulse — Internal Team Demo

**Luotea Hackathon 2026** prototype showing **reactive → predictive** maintenance using real hackathon data.

No ML required — uses **statistics (z-scores, baselines)** and **rule-based recommendations**.

## Three audiences — three views

Click **Owner | Manager | Technician** in the header. Same data pipeline, different language:

| Role | They care about | What they see |
|------|-----------------|---------------|
| **Owner / Investor** | Returns, ESG, portfolio comparability | Reliability index (A–D), portfolio table, ESG summary, decisions to approve |
| **Property Manager** | Efficiency, situational awareness, cost | Risk chart, signals, SLA/reactive %, calendar vs risk, action queue |
| **Field Technician** | Tasks, locations, checklists | Risk-ranked task cards, alarm context, step-by-step field instructions |

## What it demonstrates

| Theme | How the demo shows it |
|-------|----------------------|
| **Reactive → Predictive** | Side-by-side comparison on each building |
| **Normal vs elevated risk** | Weekly alarm / CO₂ chart with baseline band + risk score |
| **Automated actions** | P1/P2/P3 recommendations for owner, manager, technician |

## Buildings included

1. **Lentokentänkatu 11** — alarms + work orders + maintenance calendar (Valmet)
2. **Aurora House** — Smartti CO₂/climate + incidents (NovaProp)

## Quick start

```powershell
cd riskpulse
pip install -r requirements.txt

# Step 1: preprocess hackathon data (~30 sec first time)
cd backend
python preprocess.py

# Step 2: start demo server
python -m uvicorn main:app --reload --port 8080
```

Open **http://localhost:8080** in your browser.

## Team pitch flow (10 min internal)

1. **Problem** (1 min) — maintenance driven by calendar; faults visible only after alarms
2. **Live demo** (5 min) — switch buildings, show risk score, chart spike vs baseline, read 2–3 actions
3. **Architecture** (2 min) — data → signals → decisions; your team can extend rules/API
4. **Next steps** (2 min) — add KONE elevator data, LLM tech instructions, mobile view

## Project structure

```
riskpulse/
  backend/
    preprocess.py      # Reads CSV/JSON from repo root → compact JSON
    risk_engine.py     # Baseline + z-score risk scoring
    recommendations.py # Rule-based action cards
    main.py            # FastAPI API + serves frontend
  frontend/
    index.html         # Demo dashboard
  data/processed/      # Generated (gitignore optional)
```

## API endpoints

- `GET /api/buildings` — list buildings
- `GET /api/buildings/{id}/analysis` — risk analysis + recommendations
- `GET /api/health` — check data is preprocessed

## Extending (for your 4 techs)

| Person | Task |
|--------|------|
| Backend | Add Meridian Tower KONE + Smartti fusion |
| Backend | Wire OpenAI for Finnish alarm → technician checklist |
| Frontend | Role toggle (owner / manager / tech) |
| Data | Room utilization → cleaning risk signal |

## Notes

- First run **must** execute `preprocess.py` (reads from parent repo datasets)
- Risk scoring is intentionally simple and explainable for judges
- Finnish alarm/incident text is preserved — good for authenticity in pitch
