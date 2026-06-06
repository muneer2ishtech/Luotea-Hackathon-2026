# RiskPulse — Developer Guide

Technical setup, run instructions, and API reference for the RiskPulse demo.

**Project overview, pitch, and screenshots → [`../README.md`](../README.md)**

---

## Prerequisites

| Requirement | Notes |
|-------------|--------|
| **Python 3.14+** | Local dev; Docker image uses `python:3.14-slim` |
| **Organizer data** | Sibling folder `../../Luotea-Hackathon-2026/` (read-only) |
| **Git Bash** (Windows) | Recommended terminal; `start.sh` provided |
| **Docker Desktop** | Optional; easiest way to run without local Python setup |

**Default port:** `8090`

---

## Repository layout

```
riskpulse/
  backend/          # FastAPI, preprocess, risk engines, recommendations
  frontend/         # Dashboard HTML/JS/CSS
  data/processed/   # Generated locally (gitignored — run preprocess.py)
  Dockerfile
  docker-compose.yml
  start.sh          # Git Bash
  start.ps1         # PowerShell
  requirements.txt
```

---

## Quick start (local)

```bash
cd lh2026/riskpulse
pip install -r requirements.txt

# 1. Build processed JSON from hackathon datasets (~30 sec)
cd backend
python preprocess.py

# 2. Start server (default port 8090)
cd ..
./start.sh
```

Open:

- http://localhost:8090/riskpulse-no-ml — statistics, baselines, rules
- http://localhost:8090/riskpulse-ml — Isolation Forest + forecast + escalation probability

### Custom port

```bash
PORT=9000 ./start.sh

# or manually
cd backend
python -m uvicorn main:app --reload --port 9000

# PowerShell
$env:PORT=9000; .\start.ps1
```

### Stop the server

**Ctrl+C** in the terminal where it runs.

If port 8090 stays stuck on Windows:

```bash
netstat -ano | grep :8090
taskkill //PID <pid> //F
```

---

## Docker

Requires organizer data at `../../Luotea-Hackathon-2026` relative to `riskpulse/`.

**Stop any local server on 8090 first** — Docker needs the port free.

```bash
cd lh2026/riskpulse

# Foreground
docker compose up --build

# Background
docker compose up --build -d
docker compose logs -f
docker compose down
```

Custom port: `PORT=9000 docker compose up --build`

Verify:

```bash
curl http://localhost:8090/api/health
# expect: "available_buildings": 7
```

Without compose:

```bash
docker build -t riskpulse .
docker run --rm -p 8090:8090 \
  -v /path/to/Luotea-Hackathon-2026:/data/hackathon:ro \
  -e HACKATHON_DATA=/data/hackathon \
  riskpulse
```

---

## Buildings (API ids)

| ID | Site | Profile |
|----|------|---------|
| `lentokentankatu_11` | Lentokentänkatu 11 | alarm |
| `venttiilitehdas` | Venttiilitehdas | alarm + Smartti |
| `toimistotalo` | Toimistotalo | alarm |
| `std_tehdas` | STD tehdas | alarm |
| `meridian_tower` | Meridian Tower | smartti + KONE |
| `aurora_house` | Aurora House | smartti + KONE |
| `horizon_plaza` | Horizon Plaza | smartti + KONE |

Configured in `backend/config.py`. Data paths point at the organizer repo via `HACKATHON_DATA` (env var) or default sibling path.

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Preprocess status, building count |
| `GET` | `/api/riskpulse-no-ml/buildings` | List buildings (stats mode) |
| `GET` | `/api/riskpulse-no-ml/buildings/{id}/analysis` | Risk + recommendations + audiences |
| `GET` | `/api/riskpulse-ml/buildings/{id}/analysis` | ML analysis + recommendations |
| `GET` | `/api/riskpulse-no-ml/portfolio` | Cross-building owner summary |
| `GET` | `/api/riskpulse-ml/portfolio` | Same, ML mode |

---

## Backend modules

| File | Role |
|------|------|
| `preprocess.py` | CSV/JSON from organizer repo → `data/processed/*.json` |
| `config.py` | Building registry, data paths |
| `risk_engine.py` | Baselines, z-scores, risk scoring |
| `risk_engine_ml.py` | Isolation Forest, forecast, escalation probability |
| `recommendations.py` | Rule-based P1/P2/P3 action cards |
| `recommendations_ml.py` | ML-aware recommendations |
| `audiences.py` | Owner / manager / technician view builders |
| `main.py` | FastAPI app, dual routers, static frontend |

---

## Extending

| Area | Idea |
|------|------|
| Backend | OpenAI: Finnish alarm text → technician checklist |
| Frontend | Mobile-friendly technician layout |
| Data | Room utilization → cleaning risk signal |
| ML | Per-building profile tuning |

---

## Developer notes

- First run **must** run `python preprocess.py` (or let Docker entrypoint do it).
- `data/processed/*.json` is **gitignored** — each machine generates its own copy.
- Do **not** commit to the organizer `Luotea-Hackathon-2026` repo; team work stays in `lh2026`.
- Scoring is intentionally simple and explainable for demo and jury questions.
- Finnish alarm/incident text is preserved in processed data.

---

<p align="center">
  <a href="../README.md">← Back to project overview</a>
</p>
