import os
from pathlib import Path

# lh2026/riskpulse/backend → team repo is lh2026; organizer data is sibling folder
TEAM_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_HACKATHON_DATA = TEAM_ROOT.parent / "Luotea-Hackathon-2026"
HACKATHON_DATA = Path(os.environ.get("HACKATHON_DATA", _DEFAULT_HACKATHON_DATA))

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"

ALARMS_CSV = HACKATHON_DATA / "Alarms" / "alarms.csv"
WORK_ORDERS_CSV = HACKATHON_DATA / "Work orders" / "work_orders_anonymized 1.csv"
MAINTENANCE_CSV = HACKATHON_DATA / "Maintenance schedule (EH-työt)" / "Scheduled maitenance plans.csv"
SMARTTI_DIR = HACKATHON_DATA / "Smartti"
KONE_DIR = SMARTTI_DIR / "kone"

# All hackathon sites from README (7 properties)
BUILDINGS: dict[str, dict] = {
    "lentokentankatu_11": {
        "name": "Lentokentänkatu 11",
        "customer": "Valmet Technologies Oy",
        "address": "Lentokentänkatu 11, Tampere",
        "profile": "alarm",
        "site_match": "Lentokentänkatu 11",
        "sources": ["alarms", "work_orders", "maintenance_schedule"],
    },
    "venttiilitehdas": {
        "name": "Venttiilitehdas",
        "customer": "Valmet Flow Control Oy",
        "address": "Vanha Porvoontie 229, Vantaa (Hakkila)",
        "profile": "alarm",
        "site_match": "Venttiilitehdas",
        "sources": ["alarms", "work_orders", "maintenance_schedule", "smartti_climate"],
        "smartti_json": "valmet_flow_control.json",
    },
    "toimistotalo": {
        "name": "Toimistotalo",
        "customer": "Valmet Flow Control Oy",
        "address": "Vanha Porvoontie 229, Vantaa (Hakkila)",
        "profile": "alarm",
        "site_match": "Toimistotalo",
        "sources": ["alarms", "work_orders", "maintenance_schedule"],
    },
    "std_tehdas": {
        "name": "STD tehdas",
        "customer": "Valmet Flow Control Oy",
        "address": "Vanha Porvoontie 229, Vantaa (Hakkila)",
        "profile": "alarm",
        "site_match": "STD tehdas",
        "sources": ["alarms", "work_orders"],
    },
    "aurora_house": {
        "name": "Aurora House",
        "customer": "NovaProp (anonymized)",
        "address": "Innovation Drive 14, Northville",
        "profile": "smartti",
        "site_match": "Aurora House",
        "sources": ["smartti_climate", "smartti_incidents", "kone_occupancy"],
        "smartti_json": "aurora_house.json",
        "kone_json": "Aurora_House_2026-05-27_123944-normalized.json",
    },
    "meridian_tower": {
        "name": "Meridian Tower",
        "customer": "NovaProp (anonymized)",
        "address": "Solar Avenue 3, Coastview",
        "profile": "smartti",
        "site_match": "Meridian Tower",
        "sources": ["smartti_climate", "smartti_incidents", "kone_occupancy"],
        "smartti_json": "meridian_tower.json",
        "kone_json": "Meridian_Tower_2026-05-27_124158-normalized.json",
    },
    "horizon_plaza": {
        "name": "Horizon Plaza",
        "customer": "NovaProp (anonymized)",
        "address": "Central Square 26, Lakeside",
        "profile": "smartti",
        "site_match": "Horizon Plaza",
        "sources": ["smartti_climate", "smartti_incidents", "kone_occupancy"],
        "smartti_json": "horizon_plaza.json",
        "kone_json": "Horizon_Plaza_2026-05-27_124034-normalized.json",
    },
}
