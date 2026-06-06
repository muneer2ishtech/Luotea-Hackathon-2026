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

## Buildings included (all 7 hackathon sites)

| Site | Type | Data sources |
|------|------|----------------|
| **Lentokentänkatu 11** | Valmet office | Alarms, work orders, maintenance calendar |
| **Venttiilitehdas** | Valmet factory | Alarms, work orders, maintenance, Smartti climate |
| **Toimistotalo** | Valmet office | Alarms, work orders, maintenance calendar |
| **STD tehdas** | Valmet factory | Alarms, work orders |
| **Aurora House** | NovaProp | Smartti climate, incidents, KONE occupancy |
| **Meridian Tower** | NovaProp | Smartti climate, incidents, KONE occupancy |
| **Horizon Plaza** | NovaProp | Smartti climate, incidents, KONE occupancy |

## Quick start

Organizer datasets live in `../Luotea-Hackathon-2026/` (read-only). Team code lives in `lh2026/riskpulse/`.

**Default port: `8090`**

```bash
cd /d/Practice/Luotea_Hackathon_2026/lh2026/riskpulse
pip install -r requirements.txt

# Step 1: preprocess hackathon data (~30 sec first time)
cd backend
python preprocess.py

# Step 2: start demo server (default port 8090)
cd ..
./start.sh
```

Open:

- **http://localhost:8090/riskpulse-no-ml** — statistics, baselines, rules
- **http://localhost:8090/riskpulse-ml** — Isolation Forest + forecast + escalation probability

| URL | Engine |
|-----|--------|
| `/riskpulse-no-ml` | Z-scores, baselines, rules — explainable, no trained models |
| `/riskpulse-ml` | Isolation Forest anomaly detection + linear forecast + escalation probability |

### Custom port

If `8090` is busy, pick any free port:

```bash
# Git Bash — helper script
PORT=9000 ./start.sh

# Git Bash — manual
cd backend
python -m uvicorn main:app --reload --port 9000

# PowerShell
$env:PORT=9000; .\start.ps1
```

Then open `http://localhost:<your-port>/riskpulse-no-ml` (or `/riskpulse-ml`).

### Stop the server

In the terminal where it runs: **Ctrl+C**

If the port stays stuck on Windows:

```bash
netstat -ano | grep :8090
taskkill //PID <pid> //F
```

### Docker

Requires Docker Desktop and the organizer data folder at `../../Luotea-Hackathon-2026` (relative to `riskpulse/`).

```bash
cd /d/Practice/Luotea_Hackathon_2026/lh2026/riskpulse

# Default port 8090 — preprocess runs automatically on container start
docker compose up --build

# Custom host port
PORT=9000 docker compose up --build
```

Open **http://localhost:8090/riskpulse-no-ml** (or your chosen port).

Build/run without compose:

```bash
docker build -t riskpulse .
docker run --rm -p 8090:8090 \
  -v /d/Practice/Luotea_Hackathon_2026/Luotea-Hackathon-2026:/data/hackathon:ro \
  -e HACKATHON_DATA=/data/hackathon \
  riskpulse
```

## Team pitch flow (10 min internal)

1. **Problem** (1 min) — maintenance driven by calendar; faults visible only after alarms
2. **Live demo** (5 min) — switch buildings, show risk score, chart spike vs baseline, read 2–3 actions
3. **Architecture** (2 min) — data → signals → decisions; your team can extend rules/API
4. **Next steps** (2 min) — LLM tech instructions, mobile view, room utilization signal

## Project structure

```
riskpulse/
  backend/
    preprocess.py           # Reads CSV/JSON from organizer repo → compact JSON
    config.py               # 7 buildings, data paths
    risk_engine.py          # Baseline + z-score risk scoring
    risk_engine_ml.py       # ML layer
    recommendations.py      # Rule-based action cards
    audiences.py            # Owner / manager / technician views
    main.py                 # FastAPI API + serves frontend
  frontend/
    riskpulse-no-ml.html    # Stats demo dashboard
    riskpulse-ml.html       # ML demo dashboard
    app.js, styles.css
  data/processed/           # Generated locally (not in git — run preprocess.py)
  Dockerfile, docker-compose.yml
  start.sh                  # Git Bash starter (default port 8090)
  start.ps1                 # PowerShell starter
```

## API endpoints

Both modes share the same paths under their prefix:

- `GET /api/riskpulse-no-ml/buildings` — list buildings (stats mode)
- `GET /api/riskpulse-no-ml/buildings/{id}/analysis` — risk + recommendations
- `GET /api/riskpulse-ml/buildings/{id}/analysis` — ML analysis
- `GET /api/health` — preprocess status and building count

## Extending (for your 4 techs)

| Person | Task |
|--------|------|
| Backend | Wire OpenAI for Finnish alarm → technician checklist |
| Frontend | Mobile-friendly technician layout |
| Data | Room utilization → cleaning risk signal |
| ML | Tune models per building profile |

## Notes

- First run **must** execute `preprocess.py` (reads from `Luotea-Hackathon-2026/` datasets)
- `data/processed/*.json` is gitignored — each developer generates it locally
- Risk scoring is intentionally simple and explainable for judges
- Finnish alarm/incident text is preserved — good for authenticity in pitch
