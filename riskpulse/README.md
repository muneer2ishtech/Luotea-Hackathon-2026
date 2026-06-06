# RiskPulse — Developer Guide

Setup, run instructions, and API reference for the RiskPulse demo.

**Project overview → [`../README.md`](../README.md)** · **Luotea data policy → [`../README.md#source-data`](../README.md#source-data)**

---

## Prerequisites

| Requirement | Notes |
|-------------|--------|
| **Python 3.14+** | Local dev; Docker image uses `python:3.14-slim` |
| **Git Bash** (Windows) | Recommended terminal; `start.sh` provided |
| **Docker Desktop** | Optional |

**Default port:** `8090`

---

## Source data and preprocess

Luotea hackathon datasets are **confidential** (see [Source data](../README.md#source-data)). This repository contains **team code only**.

| Path | Contents | Commit to git? |
|------|----------|----------------|
| `data/source/` | Luotea CSV/JSON copied from the organizer repo | **No** (gitignored) |
| `data/processed/` | JSON built by `preprocess.py` from `data/source/` | **No** (gitignored) |
| `backend/`, `frontend/`, etc. | Application code | **Yes** |

**Setup (once per machine):**

1. Get datasets from the [organizer repository](https://github.com/tmlehti3/Luotea-Hackathon-2026).
2. Copy the files below into `data/source/`, **keeping the same folder names**.
3. Run `python preprocess.py` in `backend/` to generate `data/processed/`.

| From organizer repo | To `data/source/` |
|---------------------|-------------------|
| `Alarms/alarms.csv` | `Alarms/alarms.csv` |
| `Work orders/work_orders_anonymized 1.csv` | `Work orders/work_orders_anonymized 1.csv` |
| `Maintenance schedule (EH-työt)/Scheduled maitenance plans.csv` | `Maintenance schedule (EH-työt)/Scheduled maitenance plans.csv` |
| `Smartti/aurora_house.json` | `Smartti/aurora_house.json` |
| `Smartti/meridian_tower.json` | `Smartti/meridian_tower.json` |
| `Smartti/horizon_plaza.json` | `Smartti/horizon_plaza.json` |
| `Smartti/valmet_flow_control.json` | `Smartti/valmet_flow_control.json` |
| `Smartti/kone/Aurora_House_2026-05-27_123944-normalized.json` | `Smartti/kone/Aurora_House_2026-05-27_123944-normalized.json` |
| `Smartti/kone/Meridian_Tower_2026-05-27_124158-normalized.json` | `Smartti/kone/Meridian_Tower_2026-05-27_124158-normalized.json` |
| `Smartti/kone/Horizon_Plaza_2026-05-27_124034-normalized.json` | `Smartti/kone/Horizon_Plaza_2026-05-27_124034-normalized.json` |

Example (Git Bash, from the `riskpulse/` directory):

```bash
ORG="/d/path/to/Luotea-Hackathon-2026"   # organizer clone, not this repo
DST="data/source"
mkdir -p "$DST/Alarms" "$DST/Work orders" "$DST/Maintenance schedule (EH-työt)" "$DST/Smartti/kone"
cp "$ORG/Alarms/alarms.csv" "$DST/Alarms/"
cp "$ORG/Work orders/work_orders_anonymized 1.csv" "$DST/Work orders/"
cp "$ORG/Maintenance schedule (EH-työt)/Scheduled maitenance plans.csv" "$DST/Maintenance schedule (EH-työt)/"
cp "$ORG/Smartti/"*.json "$DST/Smartti/"
cp "$ORG/Smartti/kone/"*_normalized.json "$DST/Smartti/kone/"

cd backend
python preprocess.py
```

**After setup:**

- Run `python preprocess.py` in `backend/` after updating files in `data/source/`.
- `data/source/` and `data/processed/` are **gitignored**; never commit Luotea dataset files.
- Team code changes belong in this repository only (`Luotea-Hackathon-2026`).

---

## Repository layout

```
riskpulse/
  backend/
  frontend/
  data/
    source/       # Luotea files you copy (gitignored)
    processed/    # Output of preprocess.py (gitignored)
  Dockerfile
  docker-compose.yml
  start.sh
  start.ps1
  requirements.txt
```

---

## Quick start (local)

```bash
git clone https://github.com/muneer2ishtech/Luotea-Hackathon-2026.git
cd Luotea-Hackathon-2026/riskpulse
pip install -r requirements.txt

# Source data + preprocess — see section above (once per machine)

./start.sh
```

Open:

- http://localhost:8090/riskpulse-no-ml
- http://localhost:8090/riskpulse-ml

### Custom port

```bash
PORT=9000 ./start.sh
```

```bash
cd backend
python -m uvicorn main:app --reload --port 9000
```

```powershell
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

Complete **Source data and preprocess** first. Docker mounts `data/source/` read-only.

**Stop any local server on 8090 first.**

```bash
cd Luotea-Hackathon-2026/riskpulse
docker compose up --build
docker compose up --build -d   # background
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
  -v "$(pwd)/data/source:/app/data/source:ro" \
  -e SOURCE_DATA_DIR=/app/data/source \
  riskpulse
```

---

## Buildings (API ids)

| ID | Site | Profile |
|----|------|---------|
| `lentokentankatu_11` | Lentokentänkatu 11 | alarm |
| `toimistotalo` | Toimistotalo | alarm |
| `venttiilitehdas` | Venttiilitehdas | alarm + Smartti |
| `std_tehdas` | STD tehdas | alarm |
| `aurora_house` | Aurora House | smartti + KONE |
| `meridian_tower` | Meridian Tower | smartti + KONE |
| `horizon_plaza` | Horizon Plaza | smartti + KONE |

Configured in `backend/config.py`.

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Source/processed paths, building count |
| `GET` | `/api/riskpulse-no-ml/buildings` | List buildings (stats mode) |
| `GET` | `/api/riskpulse-no-ml/buildings/{id}/analysis` | Risk + recommendations + audiences |
| `GET` | `/api/riskpulse-ml/buildings/{id}/analysis` | ML analysis + recommendations |
| `GET` | `/api/riskpulse-no-ml/portfolio` | Cross-building owner summary |
| `GET` | `/api/riskpulse-ml/portfolio` | Same, ML mode |

---

## Backend modules

| File | Role |
|------|------|
| `preprocess.py` | `data/source/` → `data/processed/*.json` |
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
