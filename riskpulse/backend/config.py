from pathlib import Path

# lh2026/riskpulse/backend → team repo is lh2026; organizer data is sibling folder
TEAM_ROOT = Path(__file__).resolve().parents[2]
HACKATHON_DATA = TEAM_ROOT.parent / "Luotea-Hackathon-2026"

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"

ALARMS_CSV = HACKATHON_DATA / "Alarms" / "alarms.csv"
WORK_ORDERS_CSV = HACKATHON_DATA / "Work orders" / "work_orders_anonymized 1.csv"
MAINTENANCE_CSV = HACKATHON_DATA / "Maintenance schedule (EH-työt)" / "Scheduled maitenance plans.csv"
AURORA_SMARTTI = HACKATHON_DATA / "Smartti" / "aurora_house.json"

BUILDINGS = {
    "lentokentankatu_11": {
        "name": "Lentokentänkatu 11",
        "customer": "Valmet Technologies Oy",
        "address": "Lentokentänkatu 11, Tampere",
        "sources": ["alarms", "work_orders", "maintenance_schedule"],
        "site_match": "Lentokentänkatu 11",
    },
    "aurora_house": {
        "name": "Aurora House",
        "customer": "NovaProp (anonymized)",
        "address": "Innovation Drive 14, Northville",
        "sources": ["smartti_climate", "smartti_incidents"],
        "site_match": "Aurora House",
    },
}
