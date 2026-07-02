from flask import Flask, render_template, request, jsonify, redirect, url_for, session, make_response
import json, os, uuid, secrets, logging, time
import requests
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix

load_dotenv() # Load environment variables from .env

# ── Configuration & Constants ───────────────────────────────────────────
PLAYER_COLORS = {
    "Jai": "#a855f7",      # Purple
    "Piyush": "#3b82f6",   # Blue
    "Deepanshu": "#ef4444",# Red
    "Dima": "#14b8a6",     # Teal
    "Bhavya": "#ec4899",   # Pink
    "Lalit": "#f97316",    # Orange
    "Gabu": "#22c55e",     # Green
}

def get_player_color(name):
    return PLAYER_COLORS.get(name, "#64748b")

def get_next_match(fx_data):
    from datetime import timezone
    now = datetime.now(timezone.utc)
    upcoming = []
    for f in fx_data.get("fixtures", []):
        if f.get("status") in ("SCHEDULED", "TIMED"):
            try:
                utc_str = f.get("utc")
                if not utc_str: continue
                dt = datetime.strptime(utc_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                if dt > now: upcoming.append((dt, f))
            except: continue
    upcoming.sort(key=lambda x: x[0])
    return upcoming[0][1] if upcoming else None

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

@app.context_processor
def inject_globals():
    return dict(get_player_color=get_player_color)
_secret_key = os.environ.get("SECRET_KEY")
if not _secret_key:
    _secret_key = secrets.token_hex(32)
    logging.warning("SECRET_KEY not set; using a random key. Sessions will not persist across restarts.")
app.secret_key = _secret_key


@app.after_request
def _add_no_cache_headers(resp):
    if request.path.startswith("/admin"):
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
    return resp

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "league.json")

TEAMS = [
    # UEFA (16)
    {"name":"France","flag":"🇫🇷","conf":"UEFA"},
    {"name":"Spain","flag":"🇪🇸","conf":"UEFA"},
    {"name":"England","flag":"🏴󠁧󠁢󠁥󠁮󠁧󠁿","conf":"UEFA"},
    {"name":"Germany","flag":"🇩🇪","conf":"UEFA"},
    {"name":"Portugal","flag":"🇵🇹","conf":"UEFA"},
    {"name":"Netherlands","flag":"🇳🇱","conf":"UEFA"},
    {"name":"Belgium","flag":"🇧🇪","conf":"UEFA"},
    {"name":"Croatia","flag":"🇭🇷","conf":"UEFA"},
    {"name":"Switzerland","flag":"🇨🇭","conf":"UEFA"},
    {"name":"Norway","flag":"🇳🇴","conf":"UEFA"},
    {"name":"Scotland","flag":"🏴󠁧󠁢󠁳󠁣󠁴󠁿","conf":"UEFA"},
    {"name":"Austria","flag":"🇦🇹","conf":"UEFA"},
    {"name":"Bosnia and Herzegovina","flag":"🇧🇦","conf":"UEFA"},
    {"name":"Sweden","flag":"🇸🇪","conf":"UEFA"},
    {"name":"Türkiye","flag":"🇹🇷","conf":"UEFA"},
    {"name":"Czechia","flag":"🇨🇿","conf":"UEFA"},
    # CONMEBOL (6)
    {"name":"Argentina","flag":"🇦🇷","conf":"CONMEBOL"},
    {"name":"Brazil","flag":"🇧🇷","conf":"CONMEBOL"},
    {"name":"Colombia","flag":"🇨🇴","conf":"CONMEBOL"},
    {"name":"Ecuador","flag":"🇪🇨","conf":"CONMEBOL"},
    {"name":"Paraguay","flag":"🇵🇾","conf":"CONMEBOL"},
    {"name":"Uruguay","flag":"🇺🇾","conf":"CONMEBOL"},
    # CONCACAF (6 — 3 hosts + 3 qualifiers)
    {"name":"USA","flag":"🇺🇸","conf":"CONCACAF"},
    {"name":"Canada","flag":"🇨🇦","conf":"CONCACAF"},
    {"name":"Mexico","flag":"🇲🇽","conf":"CONCACAF"},
    {"name":"Panama","flag":"🇵🇦","conf":"CONCACAF"},
    {"name":"Curaçao","flag":"🇨🇼","conf":"CONCACAF"},
    {"name":"Haiti","flag":"🇭🇹","conf":"CONCACAF"},
    # AFC (8)
    {"name":"Japan","flag":"🇯🇵","conf":"AFC"},
    {"name":"Iran","flag":"🇮🇷","conf":"AFC"},
    {"name":"Jordan","flag":"🇯🇴","conf":"AFC"},
    {"name":"South Korea","flag":"🇰🇷","conf":"AFC"},
    {"name":"Uzbekistan","flag":"🇺🇿","conf":"AFC"},
    {"name":"Australia","flag":"🇦🇺","conf":"AFC"},
    {"name":"Qatar","flag":"🇶🇦","conf":"AFC"},
    {"name":"Saudi Arabia","flag":"🇸🇦","conf":"AFC"},
    # CAF (9)
    {"name":"Algeria","flag":"🇩🇿","conf":"CAF"},
    {"name":"Cape Verde","flag":"🇨🇻","conf":"CAF"},
    {"name":"Egypt","flag":"🇪🇬","conf":"CAF"},
    {"name":"Ghana","flag":"🇬🇭","conf":"CAF"},
    {"name":"Ivory Coast","flag":"🇨🇮","conf":"CAF"},
    {"name":"Morocco","flag":"🇲🇦","conf":"CAF"},
    {"name":"Senegal","flag":"🇸🇳","conf":"CAF"},
    {"name":"South Africa","flag":"🇿🇦","conf":"CAF"},
    {"name":"Tunisia","flag":"🇹🇳","conf":"CAF"},
    # OFC (1)
    {"name":"New Zealand","flag":"🇳🇿","conf":"OFC"},
    # Interconfederation playoffs (2)
    {"name":"DR Congo","flag":"🇨🇩","conf":"CAF"},
    {"name":"Iraq","flag":"🇮🇶","conf":"AFC"},
]

DEFAULT_TIERS = {
    "1": ["France","Spain","England","Germany","Portugal","Netherlands","Argentina","Brazil"],
    "2": ["Belgium","Croatia","Uruguay","Colombia","USA","Japan","Morocco","Senegal"],
    "3": ["Switzerland","Austria","South Korea","Mexico","Canada","Ecuador","Ivory Coast","Egypt"],
    "4": ["Norway","Scotland","Sweden","Türkiye","Czechia","Bosnia and Herzegovina","Paraguay","Australia"],
    "5": ["Saudi Arabia","Iran","Ghana","Tunisia","Algeria","South Africa","Panama","Qatar"],
    "6": ["Jordan","Uzbekistan","Cape Verde","New Zealand","Curaçao","Haiti","DR Congo","Iraq"],
}

STAGE_WIN_PTS = {"group":6,"r32":8,"r16":10,"qf":15,"sf":20,"final":40}
VALID_STAGES = {"group", "r32", "r16", "qf", "sf", "final"}
TEAM_NAMES = {t["name"] for t in TEAMS}

WC2026_GROUPS = {
    "A": ["Mexico","South Africa","South Korea","Czechia"],
    "B": ["Canada","Bosnia and Herzegovina","Qatar","Switzerland"],
    "C": ["Brazil","Morocco","Haiti","Scotland"],
    "D": ["USA","Paraguay","Australia","Türkiye"],
    "E": ["Germany","Curaçao","Ivory Coast","Ecuador"],
    "F": ["Netherlands","Japan","Sweden","Tunisia"],
    "G": ["Belgium","Egypt","Iran","New Zealand"],
    "H": ["Spain","Cape Verde","Saudi Arabia","Uruguay"],
    "I": ["France","Senegal","Iraq","Norway"],
    "J": ["Argentina","Algeria","Austria","Jordan"],
    "K": ["Portugal","DR Congo","Uzbekistan","Colombia"],
    "L": ["England","Croatia","Ghana","Panama"],
}

WC2026_FIXTURES = [
    # ── Group A: Mexico, South Africa, South Korea, Czechia ──────────────────
    # MD1: Jun 11
    {"round": "Group A", "stage": "group", "home": "Mexico",       "away": "South Africa", "date": "11 Jun 2026", "group": "A"},
    {"round": "Group A", "stage": "group", "home": "South Korea",  "away": "Czechia",       "date": "11 Jun 2026", "group": "A"},
    # MD2: Jun 18 (swapped to correct official order)
    {"round": "Group A", "stage": "group", "home": "Mexico",       "away": "South Korea",   "date": "18 Jun 2026", "group": "A"},
    {"round": "Group A", "stage": "group", "home": "South Africa", "away": "Czechia",        "date": "18 Jun 2026", "group": "A"},
    # MD3: Jun 24 (simultaneous)
    {"round": "Group A", "stage": "group", "home": "Czechia",      "away": "Mexico",         "date": "24 Jun 2026", "group": "A"},
    {"round": "Group A", "stage": "group", "home": "South Africa", "away": "South Korea",    "date": "24 Jun 2026", "group": "A"},

    # ── Group B: Canada, Bosnia and Herzegovina, Qatar, Switzerland ──────────
    # MD1: Jun 12
    {"round": "Group B", "stage": "group", "home": "Canada",                  "away": "Bosnia and Herzegovina", "date": "12 Jun 2026", "group": "B"},
    {"round": "Group B", "stage": "group", "home": "Qatar",                   "away": "Switzerland",            "date": "13 Jun 2026", "group": "B"},
    # MD2: Jun 18
    {"round": "Group B", "stage": "group", "home": "Switzerland",             "away": "Bosnia and Herzegovina", "date": "18 Jun 2026", "group": "B"},
    {"round": "Group B", "stage": "group", "home": "Canada",                  "away": "Qatar",                  "date": "18 Jun 2026", "group": "B"},
    # MD3: Jun 24 (simultaneous)
    {"round": "Group B", "stage": "group", "home": "Switzerland",             "away": "Canada",                 "date": "24 Jun 2026", "group": "B"},
    {"round": "Group B", "stage": "group", "home": "Bosnia and Herzegovina",  "away": "Qatar",                  "date": "24 Jun 2026", "group": "B"},

    # ── Group C: Brazil, Morocco, Haiti, Scotland ─────────────────────────────
    # MD1: Jun 13
    {"round": "Group C", "stage": "group", "home": "Brazil",   "away": "Morocco",   "date": "13 Jun 2026", "group": "C"},
    {"round": "Group C", "stage": "group", "home": "Haiti",    "away": "Scotland",  "date": "13 Jun 2026", "group": "C"},
    # MD2: Jun 19
    {"round": "Group C", "stage": "group", "home": "Brazil",   "away": "Haiti",     "date": "19 Jun 2026", "group": "C"},
    {"round": "Group C", "stage": "group", "home": "Scotland", "away": "Morocco",   "date": "19 Jun 2026", "group": "C"},
    # MD3: Jun 24 (simultaneous)
    {"round": "Group C", "stage": "group", "home": "Scotland", "away": "Brazil",    "date": "24 Jun 2026", "group": "C"},
    {"round": "Group C", "stage": "group", "home": "Morocco",  "away": "Haiti",     "date": "24 Jun 2026", "group": "C"},

    # ── Group D: USA, Paraguay, Australia, Türkiye ────────────────────────────
    # MD1: Jun 12–13
    {"round": "Group D", "stage": "group", "home": "USA",       "away": "Paraguay",   "date": "12 Jun 2026", "group": "D"},
    {"round": "Group D", "stage": "group", "home": "Australia", "away": "Türkiye",    "date": "13 Jun 2026", "group": "D"},
    # MD2: Jun 19
    {"round": "Group D", "stage": "group", "home": "USA",       "away": "Australia",  "date": "19 Jun 2026", "group": "D"},
    {"round": "Group D", "stage": "group", "home": "Türkiye",   "away": "Paraguay",   "date": "19 Jun 2026", "group": "D"},
    # MD3: Jun 25 (simultaneous)
    {"round": "Group D", "stage": "group", "home": "Türkiye",   "away": "USA",        "date": "25 Jun 2026", "group": "D"},
    {"round": "Group D", "stage": "group", "home": "Paraguay",  "away": "Australia",  "date": "25 Jun 2026", "group": "D"},

    # ── Group E: Germany, Curaçao, Ivory Coast, Ecuador ──────────────────────
    # MD1: Jun 14
    {"round": "Group E", "stage": "group", "home": "Germany",     "away": "Curaçao",      "date": "14 Jun 2026", "group": "E"},
    {"round": "Group E", "stage": "group", "home": "Ivory Coast", "away": "Ecuador",      "date": "14 Jun 2026", "group": "E"},
    # MD2: Jun 20
    {"round": "Group E", "stage": "group", "home": "Germany",     "away": "Ivory Coast",  "date": "20 Jun 2026", "group": "E"},
    {"round": "Group E", "stage": "group", "home": "Ecuador",     "away": "Curaçao",      "date": "20 Jun 2026", "group": "E"},
    # MD3: Jun 25 (simultaneous)
    {"round": "Group E", "stage": "group", "home": "Curaçao",     "away": "Ivory Coast",  "date": "25 Jun 2026", "group": "E"},
    {"round": "Group E", "stage": "group", "home": "Ecuador",     "away": "Germany",      "date": "25 Jun 2026", "group": "E"},

    # ── Group F: Netherlands, Japan, Sweden, Tunisia ──────────────────────────
    # MD1: Jun 14
    {"round": "Group F", "stage": "group", "home": "Netherlands", "away": "Japan",        "date": "14 Jun 2026", "group": "F"},
    {"round": "Group F", "stage": "group", "home": "Sweden",      "away": "Tunisia",      "date": "14 Jun 2026", "group": "F"},
    # MD2: Jun 20
    {"round": "Group F", "stage": "group", "home": "Netherlands", "away": "Sweden",       "date": "20 Jun 2026", "group": "F"},
    {"round": "Group F", "stage": "group", "home": "Tunisia",     "away": "Japan",        "date": "20 Jun 2026", "group": "F"},
    # MD3: Jun 25 (simultaneous)
    {"round": "Group F", "stage": "group", "home": "Japan",       "away": "Sweden",       "date": "25 Jun 2026", "group": "F"},
    {"round": "Group F", "stage": "group", "home": "Tunisia",     "away": "Netherlands",  "date": "25 Jun 2026", "group": "F"},

    # ── Group G: Belgium, Egypt, Iran, New Zealand ────────────────────────────
    # MD1: Jun 15
    {"round": "Group G", "stage": "group", "home": "Belgium",     "away": "Egypt",        "date": "15 Jun 2026", "group": "G"},
    {"round": "Group G", "stage": "group", "home": "Iran",        "away": "New Zealand",  "date": "15 Jun 2026", "group": "G"},
    # MD2: Jun 21
    {"round": "Group G", "stage": "group", "home": "Belgium",     "away": "Iran",         "date": "21 Jun 2026", "group": "G"},
    {"round": "Group G", "stage": "group", "home": "New Zealand", "away": "Egypt",        "date": "21 Jun 2026", "group": "G"},
    # MD3: Jun 26 (simultaneous)
    {"round": "Group G", "stage": "group", "home": "Egypt",       "away": "Iran",         "date": "26 Jun 2026", "group": "G"},
    {"round": "Group G", "stage": "group", "home": "New Zealand", "away": "Belgium",      "date": "26 Jun 2026", "group": "G"},

    # ── Group H: Spain, Cape Verde, Saudi Arabia, Uruguay ────────────────────
    # MD1: Jun 15
    {"round": "Group H", "stage": "group", "home": "Spain",        "away": "Cape Verde",   "date": "15 Jun 2026", "group": "H"},
    {"round": "Group H", "stage": "group", "home": "Saudi Arabia", "away": "Uruguay",      "date": "15 Jun 2026", "group": "H"},
    # MD2: Jun 21
    {"round": "Group H", "stage": "group", "home": "Spain",        "away": "Saudi Arabia", "date": "21 Jun 2026", "group": "H"},
    {"round": "Group H", "stage": "group", "home": "Uruguay",      "away": "Cape Verde",   "date": "21 Jun 2026", "group": "H"},
    # MD3: Jun 26 (simultaneous)
    {"round": "Group H", "stage": "group", "home": "Cape Verde",   "away": "Saudi Arabia", "date": "26 Jun 2026", "group": "H"},
    {"round": "Group H", "stage": "group", "home": "Uruguay",      "away": "Spain",        "date": "26 Jun 2026", "group": "H"},

    # ── Group I: France, Senegal, Iraq, Norway ────────────────────────────────
    # MD1: Jun 16
    {"round": "Group I", "stage": "group", "home": "France",  "away": "Senegal",  "date": "16 Jun 2026", "group": "I"},
    {"round": "Group I", "stage": "group", "home": "Iraq",    "away": "Norway",   "date": "16 Jun 2026", "group": "I"},
    # MD2: Jun 22
    {"round": "Group I", "stage": "group", "home": "France",  "away": "Iraq",     "date": "22 Jun 2026", "group": "I"},
    {"round": "Group I", "stage": "group", "home": "Norway",  "away": "Senegal",  "date": "22 Jun 2026", "group": "I"},
    # MD3: Jun 26 (simultaneous)
    {"round": "Group I", "stage": "group", "home": "Norway",  "away": "France",   "date": "26 Jun 2026", "group": "I"},
    {"round": "Group I", "stage": "group", "home": "Senegal", "away": "Iraq",     "date": "26 Jun 2026", "group": "I"},

    # ── Group J: Argentina, Algeria, Austria, Jordan ──────────────────────────
    # MD1: Jun 16
    {"round": "Group J", "stage": "group", "home": "Argentina", "away": "Algeria",    "date": "16 Jun 2026", "group": "J"},
    {"round": "Group J", "stage": "group", "home": "Austria",   "away": "Jordan",     "date": "16 Jun 2026", "group": "J"},
    # MD2: Jun 22
    {"round": "Group J", "stage": "group", "home": "Argentina", "away": "Austria",    "date": "22 Jun 2026", "group": "J"},
    {"round": "Group J", "stage": "group", "home": "Jordan",    "away": "Algeria",    "date": "22 Jun 2026", "group": "J"},
    # MD3: Jun 27 (simultaneous)
    {"round": "Group J", "stage": "group", "home": "Algeria",   "away": "Austria",    "date": "27 Jun 2026", "group": "J"},
    {"round": "Group J", "stage": "group", "home": "Jordan",    "away": "Argentina",  "date": "27 Jun 2026", "group": "J"},

    # ── Group K: Portugal, DR Congo, Uzbekistan, Colombia ────────────────────
    # MD1: Jun 17
    {"round": "Group K", "stage": "group", "home": "Portugal",   "away": "DR Congo",    "date": "17 Jun 2026", "group": "K"},
    {"round": "Group K", "stage": "group", "home": "Uzbekistan", "away": "Colombia",    "date": "17 Jun 2026", "group": "K"},
    # MD2: Jun 23
    {"round": "Group K", "stage": "group", "home": "Portugal",   "away": "Uzbekistan",  "date": "23 Jun 2026", "group": "K"},
    {"round": "Group K", "stage": "group", "home": "Colombia",   "away": "DR Congo",    "date": "23 Jun 2026", "group": "K"},
    # MD3: Jun 27 (simultaneous)
    {"round": "Group K", "stage": "group", "home": "Colombia",   "away": "Portugal",    "date": "27 Jun 2026", "group": "K"},
    {"round": "Group K", "stage": "group", "home": "DR Congo",   "away": "Uzbekistan",  "date": "27 Jun 2026", "group": "K"},

    # ── Group L: England, Croatia, Ghana, Panama ──────────────────────────────
    # MD1: Jun 17
    {"round": "Group L", "stage": "group", "home": "England", "away": "Croatia",  "date": "17 Jun 2026", "group": "L"},
    {"round": "Group L", "stage": "group", "home": "Ghana",   "away": "Panama",   "date": "17 Jun 2026", "group": "L"},
    # MD2: Jun 23
    {"round": "Group L", "stage": "group", "home": "England", "away": "Ghana",    "date": "23 Jun 2026", "group": "L"},
    {"round": "Group L", "stage": "group", "home": "Panama",  "away": "Croatia",  "date": "23 Jun 2026", "group": "L"},
    # MD3: Jun 27 (simultaneous)
    {"round": "Group L", "stage": "group", "home": "Panama",  "away": "England",  "date": "27 Jun 2026", "group": "L"},
    {"round": "Group L", "stage": "group", "home": "Croatia", "away": "Ghana",    "date": "27 Jun 2026", "group": "L"},
]

WC2026_R32_ACTUAL_TEAMS = {
    73: ("South Africa", "Canada"),
    74: ("Germany", "Paraguay"),
    75: ("Netherlands", "Morocco"),
    76: ("Brazil", "Japan"),
    77: ("France", "Sweden"),
    78: ("Ivory Coast", "Norway"),
    79: ("Mexico", "Ecuador"),
    80: ("England", "DR Congo"),
    81: ("USA", "Bosnia and Herzegovina"),
    82: ("Belgium", "Senegal"),
    83: ("Portugal", "Croatia"),
    84: ("Spain", "Austria"),
    85: ("Switzerland", "Algeria"),
    86: ("Argentina", "Cape Verde"),
    87: ("Colombia", "Ghana"),
    88: ("Australia", "Egypt"),
}


WC2026_R32_BRACKET = [
    {"match": 73, "date": "28 Jun 2026", "slot_a": ("2nd", "A"), "slot_b": ("2nd", "B")},
    {"match": 74, "date": "29 Jun 2026", "slot_a": ("1st", "E"), "slot_b": ("3rd", None)},
    {"match": 75, "date": "29 Jun 2026", "slot_a": ("1st", "F"), "slot_b": ("2nd", "C")},
    {"match": 76, "date": "29 Jun 2026", "slot_a": ("1st", "C"), "slot_b": ("2nd", "F")},
    {"match": 77, "date": "29 Jun 2026", "slot_a": ("1st", "I"), "slot_b": ("3rd", None)},
    {"match": 78, "date": "30 Jun 2026", "slot_a": ("2nd", "E"), "slot_b": ("2nd", "I")},
    {"match": 79, "date": "30 Jun 2026", "slot_a": ("1st", "A"), "slot_b": ("3rd", None)},
    {"match": 80, "date": "01 Jul 2026", "slot_a": ("1st", "L"), "slot_b": ("3rd", None)},
    {"match": 81, "date": "01 Jul 2026", "slot_a": ("1st", "D"), "slot_b": ("3rd", None)},
    {"match": 82, "date": "01 Jul 2026", "slot_a": ("1st", "G"), "slot_b": ("3rd", None)},
    {"match": 83, "date": "02 Jul 2026", "slot_a": ("2nd", "K"), "slot_b": ("2nd", "L")},
    {"match": 84, "date": "02 Jul 2026", "slot_a": ("1st", "H"), "slot_b": ("2nd", "J")},
    {"match": 85, "date": "02 Jul 2026", "slot_a": ("1st", "B"), "slot_b": ("3rd", None)},
    {"match": 86, "date": "02 Jul 2026", "slot_a": ("1st", "J"), "slot_b": ("2nd", "H")},
    {"match": 87, "date": "03 Jul 2026", "slot_a": ("1st", "K"), "slot_b": ("3rd", None)},
    {"match": 88, "date": "03 Jul 2026", "slot_a": ("2nd", "D"), "slot_b": ("2nd", "G")},
]

WC2026_R16_BRACKET = [
    {"match": 89, "date": "04 Jul 2026", "r32_a": 74, "r32_b": 77},
    {"match": 90, "date": "04 Jul 2026", "r32_a": 73, "r32_b": 75},
    {"match": 91, "date": "05 Jul 2026", "r32_a": 76, "r32_b": 78},
    {"match": 92, "date": "05 Jul 2026", "r32_a": 79, "r32_b": 80},
    {"match": 93, "date": "06 Jul 2026", "r32_a": 83, "r32_b": 84},
    {"match": 94, "date": "06 Jul 2026", "r32_a": 81, "r32_b": 82},
    {"match": 95, "date": "07 Jul 2026", "r32_a": 86, "r32_b": 88},
    {"match": 96, "date": "07 Jul 2026", "r32_a": 85, "r32_b": 87},
]

POINTS_DEFAULTS = {
    "win":         {"group": 4, "r32": 4, "r16": 5, "qf": 6, "sf": 7, "final": 9},
    "draw":        2,
    "loss":        0,
    "goal":        1,
    "clean_sheet": 2,
    "penalties":   2,
    "red_card":   -1,
    "hattrick":    3,
}

ADMIN_PIN = os.environ.get("ADMIN_PIN", "1234")

FOOTBALL_API_KEY = os.environ.get("FOOTBALL_API_KEY", "d0a76a8bac3542ee9a3fe5960510b998")
FOOTBALL_API_BASE = "https://api.football-data.org/v4"
WC2026_COMPETITION = "WC"

_fetch_cache: dict = {}
CACHE_TTL = 60

def load_data():
    if not os.path.exists(DATA_FILE):
        return default_data()
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            data = json.load(f)
        data.pop("current_passes", None)
        return data
    except json.JSONDecodeError as e:
        logging.error("Corrupted data file: %s — resetting.", e)
        os.remove(DATA_FILE)
        return default_data()

def save_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, DATA_FILE)

def default_data():
    return {
        "league_name": "WC2026 Fantasy",
        "budget": 1000,
        "players": [],
        "teams_per_player": 0,
        "tiers": {k: list(v) for k, v in DEFAULT_TIERS.items()},
        "tier_prices": {"1":200,"2":150,"3":100,"4":70,"5":40,"6":20},
        "started": False,
        "auction_done": False,
        "budgets": {},
        "points": {},
        "ownership": {},
        "team_sold": {},
        "auction_queue": [],
        "auction_idx": 0,
        "current_bidder": 0,
        "current_bid": 0,
        "current_high_bidder": None,
        "auction_active_bidders": [],
        "auction_active_team": None,
        "matches": [],
    }

def get_team_tier(name, tiers):
    for t, teams in tiers.items():
        if name in teams:
            return int(t)
    return 0


def build_group_order_auction_queue(tiers: dict) -> list[str]:
    assigned = set()
    queue = []
    for group_letter, group_teams in WC2026_GROUPS.items():
        ordered = sorted(group_teams)
        for team in ordered:
            if team in TEAM_NAMES and team not in assigned:
                queue.append(team)
                assigned.add(team)
    remaining = []
    for teams in tiers.values():
        for team in teams:
            if team not in assigned:
                remaining.append(team)
                assigned.add(team)
    queue.extend(sorted(remaining))
    return queue

def get_team_flag(name):
    for t in TEAMS:
        if t["name"] == name:
            return t["flag"]
    return "🏳"


def normalize_team_name(name: str) -> str:
    if not name:
        return ""
    name = name.strip()
    mapping = {
        "Turkey": "Türkiye",
        "Trkiye": "Türkiye",
        "Bosnia-Herzegovina": "Bosnia and Herzegovina",
        "Bosnia and Herzegovina": "Bosnia and Herzegovina",
        "Congo DR": "DR Congo",
        "DR Congo": "DR Congo",
        "Cape Verde Islands": "Cape Verde",
        "Cape Verde": "Cape Verde",
    }
    return mapping.get(name, name)


def get_official_team_name(name: str) -> str:
    norm = normalize_team_name(name)
    for group_teams in WC2026_GROUPS.values():
        for t in group_teams:
            if normalize_team_name(t) == norm:
                return t
    return name


def get_team_group(name):
    norm_name = normalize_team_name(name)
    for group_letter, group_teams in WC2026_GROUPS.items():
        if norm_name in [normalize_team_name(t) for t in group_teams]:
            return group_letter
    return None


def get_player_teams_by_group(player_name, data):
    owned = data.get("ownership", {}).get(player_name, [])
    tiers = data.get("tiers", {})
    groups = {}
    
    for team in owned:
        group = get_team_group(team)
        if group not in groups:
            groups[group] = []
        groups[group].append({
            "name": team,
            "flag": get_team_flag(team),
            "group": group,
            "group_label": f"Group {group}" if group else None,
            "tier": get_team_tier(team, tiers),
        })
    
    sorted_groups = []
    for group in sorted([g for g in groups.keys() if g is not None]):
        sorted_groups.append({
            "group": group,
            "label": f"Group {group}",
            "teams": sorted(groups[group], key=lambda t: t["name"])
        })
    
    if None in groups:
        sorted_groups.append({
            "group": None,
            "label": "No Group",
            "teams": sorted(groups[None], key=lambda t: t["name"])
        })
    
    return sorted_groups


def _map_stage(api_stage: str) -> str:
    mapping = {
        "GROUP_STAGE": "group",
        "ROUND_OF_32": "r32",
        "LAST_32": "r32",
        "ROUND_OF_16": "r16",
        "LAST_16": "r16",
        "QUARTER_FINALS": "qf",
        "SEMI_FINALS": "sf",
        "FINAL": "final",
    }
    return mapping.get(api_stage.upper(), "group")


def _fetch_fallback_games():
    try:
        resp = requests.get("https://worldcup26.ir/get/games", timeout=5)
        if resp.status_code == 200:
            return resp.json().get("games", [])
    except Exception as e:
        logging.warning("requests failed to fetch from worldcup26.ir, trying curl: %s", e)
        
    try:
        import subprocess
        res = subprocess.run(["curl", "-s", "https://worldcup26.ir/get/games"], capture_output=True, text=True, timeout=8)
        if res.returncode == 0 and res.stdout:
            return json.loads(res.stdout).get("games", [])
    except Exception as e:
        logging.error("curl failed to fetch from worldcup26.ir: %s", e)
        
    return []


def _enrich_hattricks_from_fallback(team1, team2, extra):
    try:
        import re
        games = _fetch_fallback_games()
        for g in games:
            h_name = g.get("home_team_name_en")
            a_name = g.get("away_team_name_en")
            if h_name and a_name and _match_team_names(h_name, a_name, team1, team2):
                is_h_team1 = _is_name_match(h_name, team1)
                
                h_scorers = g.get("home_scorers")
                if h_scorers and h_scorers != "null":
                    entries = re.findall(r'["“]([^"密“”]+)["”]', h_scorers)
                    if not entries:
                        entries = re.findall(r'["“]([^"“”]+)["”]', h_scorers)
                    counts = {}
                    for entry in entries:
                        name = re.sub(r'\s+\d+.*?$', '', entry).strip()
                        counts[name] = counts.get(name, 0) + 1
                    if any(c >= 3 for c in counts.values()):
                        if is_h_team1: extra["hattrick_t1"] = True
                        else: extra["hattrick_t2"] = True
                        
                a_scorers = g.get("away_scorers")
                if a_scorers and a_scorers != "null":
                    entries = re.findall(r'["“]([^"“”]+)["”]', a_scorers)
                    counts = {}
                    for entry in entries:
                        name = re.sub(r'\s+\d+.*?$', '', entry).strip()
                        counts[name] = counts.get(name, 0) + 1
                    if any(c >= 3 for c in counts.values()):
                        if is_h_team1: extra["hattrick_t2"] = True
                        else: extra["hattrick_t1"] = True
                break
    except Exception as e:
        logging.error("Error during enrichment: %s", e)


def _get_api_match_score(m):
    score = m.get("score") or {}
    if score.get("duration") == "PENALTY_SHOOTOUT":
        ft = score.get("fullTime") or {}
        pen = score.get("penalties") or {}
        h = (ft.get("home") or 0) - (pen.get("home") or 0)
        a = (ft.get("away") or 0) - (pen.get("away") or 0)
        return {"home": max(0, h), "away": max(0, a)}
    else:
        ft = score.get("fullTime") or {}
        return {"home": ft.get("home") or 0, "away": ft.get("away") or 0}

def fetch_match_result(team1: str, team2: str) -> dict:
    cache_key = f"{team1}|{team2}"
    now = time.time()
    if cache_key in _fetch_cache:
        ts, payload = _fetch_cache[cache_key]
        if now - ts < CACHE_TTL:
            return payload

    # Try Football-Data.org first
    headers = {"X-Auth-Token": FOOTBALL_API_KEY} if FOOTBALL_API_KEY else {}
    try:
        resp = requests.get(
            f"{FOOTBALL_API_BASE}/competitions/{WC2026_COMPETITION}/matches",
            headers=headers, timeout=8,
        )
        if resp.status_code == 200:
            matches = resp.json().get("matches", [])
            for m in reversed(matches):
                ht_name, at_name = m["homeTeam"]["name"], m["awayTeam"]["name"]
                if _match_team_names(ht_name, at_name, team1, team2):
                    score = _get_api_match_score(m)
                    stage = _map_stage(m.get("stage", ""))
                    status = m.get("status")
                    
                    # Extract extra events (cards, hat-tricks, penalties)
                    extra = {}
                    if m["score"].get("duration") == "PENALTY_SHOOTOUT":
                        extra["penalties"] = True
                        extra["winner"] = team1 if m["score"]["winner"] == "HOME_TEAM" and _is_name_match(ht_name, team1) else team2

                    # Count red cards and hat-tricks if detailed data is present
                    # Note: Free tier might not include 'bookings' or 'goals' in the bulk matches response.
                    # If they are present, we use them.
                    rc_t1, rc_t2 = 0, 0
                    if "bookings" in m:
                        for b in m["bookings"]:
                            if b.get("type") in ("RED_CARD", "YELLOW_RED_CARD"):
                                if _is_name_match(b["team"]["name"], team1): rc_t1 += 1
                                else: rc_t2 += 1
                    if rc_t1 > 0: extra["red_card_t1"] = rc_t1
                    if rc_t2 > 0: extra["red_card_t2"] = rc_t2
                    
                    if "goals" in m:
                        counts = {}
                        for g in m["goals"]:
                            scorer = g.get("scorer", {})
                            sid = scorer.get("id") or scorer.get("name")
                            if sid: counts[sid] = counts.get(sid, 0) + 1
                        for sid, count in counts.items():
                            if count >= 3:
                                # Find team of scorer
                                scorer_team = next((g["team"]["name"] for g in m["goals"] if (g.get("scorer", {}).get("id") or g.get("scorer", {}).get("name")) == sid), "")
                                if _is_name_match(scorer_team, team1): extra["hattrick_t1"] = True
                                else: extra["hattrick_t2"] = True                    # Enrich hattricks from fallback API if not already set (e.g. on free tier)
                    if not extra.get("hattrick_t1") and not extra.get("hattrick_t2"):
                        _enrich_hattricks_from_fallback(team1, team2, extra)

                    result = {
                        "team1": team1, "team2": team2,
                        "score1": score["home"] if _is_name_match(ht_name, team1) else score["away"],
                        "score2": score["away"] if _is_name_match(ht_name, team1) else score["home"],
                        "stage": stage,
                        "status": status,
                        "extra": extra,
                        "source": "football-data.org"
                    }
                    _fetch_cache[cache_key] = (now, result)
                    return result
    except:
        pass

    # Fallback to worldcup26.ir (Open Source API)
    try:
        games = _fetch_fallback_games()
        for g in games:
            ht = g.get("home_team_name_en") or g.get("home_team")
            at = g.get("away_team_name_en") or g.get("away_team")
            if ht and at and _match_team_names(ht, at, team1, team2):
                extra = {}
                is_h_team1 = _is_name_match(ht, team1)
                
                h_scorers = g.get("home_scorers")
                if h_scorers and h_scorers != "null":
                    import re
                    entries = re.findall(r'["“]([^"“”]+)["”]', h_scorers)
                    counts = {}
                    for entry in entries:
                        name = re.sub(r'\s+\d+.*?$', '', entry).strip()
                        counts[name] = counts.get(name, 0) + 1
                    if any(c >= 3 for c in counts.values()):
                        if is_h_team1: extra["hattrick_t1"] = True
                        else: extra["hattrick_t2"] = True

                a_scorers = g.get("away_scorers")
                if a_scorers and a_scorers != "null":
                    import re
                    entries = re.findall(r'["“]([^"“”]+)["”]', a_scorers)
                    counts = {}
                    for entry in entries:
                        name = re.sub(r'\s+\d+.*?$', '', entry).strip()
                        counts[name] = counts.get(name, 0) + 1
                    if any(c >= 3 for c in counts.values()):
                        if is_h_team1: extra["hattrick_t2"] = True
                        else: extra["hattrick_t1"] = True

                h_pen = g.get("home_penalty_score")
                a_pen = g.get("away_penalty_score")
                if h_pen is not None and a_pen is not None and h_pen != "null" and a_pen != "null":
                    try:
                        h_pen_int, a_pen_int = int(h_pen), int(a_pen)
                        if h_pen_int > 0 or a_pen_int > 0:
                            extra["penalties"] = True
                            is_h_winner = h_pen_int > a_pen_int
                            extra["winner"] = team1 if (is_h_winner and is_h_team1) or (not is_h_winner and not is_h_team1) else team2
                    except ValueError:
                        pass

                result = {
                    "team1": team1, "team2": team2,
                    "score1": int(g.get("home_score")) if _is_name_match(ht, team1) else int(g.get("away_score")),
                    "score2": int(g.get("away_score")) if _is_name_match(ht, team1) else int(g.get("home_score")),
                    "stage": _map_stage_simple(g.get("type") or g.get("round")),
                    "status": "FINISHED" if str(g.get("finished")).upper() == "TRUE" else "IN_PLAY",
                    "extra": extra,
                    "source": "worldcup26.ir"
                }
                _fetch_cache[cache_key] = (now, result)
                return result
    except:
        pass

    result = {"no_result": True}
    _fetch_cache[cache_key] = (now, result)
    return result

def _is_name_match(n1, n2):
    if not n1 or not n2: return False
    n1_norm = normalize_team_name(n1).lower()
    n2_norm = normalize_team_name(n2).lower()
    if n1_norm == n2_norm: return True
    # Common variations
    synonyms = {"usa": "united states", "united states": "usa", "south korea": "republic of korea", "republic of korea": "south korea"}
    if synonyms.get(n1_norm) == n2_norm: return True
    return False

_espn_scoreboard_cache = {"ts": 0, "events": []}
ESPN_CACHE_TTL = 300

def _fetch_detailed_bookings_and_extra_espn(t1, t2, extra):
    now = time.time()
    events = []
    
    if now - _espn_scoreboard_cache["ts"] < ESPN_CACHE_TTL and _espn_scoreboard_cache["events"]:
        events = _espn_scoreboard_cache["events"]
    else:
        try:
            url = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates=20260611-20260719&limit=200"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                events = resp.json().get("events", [])
                _espn_scoreboard_cache["ts"] = now
                _espn_scoreboard_cache["events"] = events
        except Exception as e:
            logging.error("Failed to fetch ESPN scoreboard: %s", e)
            
    matched_event = None
    for e in events:
        try:
            comp = e['competitions'][0]
            home = comp['competitors'][0]['team']['displayName']
            away = comp['competitors'][1]['team']['displayName']
            if (_is_name_match(home, t1) and _is_name_match(away, t2)) or (_is_name_match(home, t2) and _is_name_match(away, t1)):
                matched_event = e
                break
        except Exception:
            continue
            
    if not matched_event:
        return
        
    game_id = matched_event['id']
    try:
        summary_url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary?event={game_id}"
        s_resp = requests.get(summary_url, timeout=10)
        if s_resp.status_code == 200:
            data = s_resp.json()
            key_events = data.get("keyEvents", [])
            rc_t1, rc_t2 = 0, 0
            
            for event in key_events:
                evt_type = event.get("type", {})
                evt_type_code = str(evt_type.get("type")).lower()
                evt_text = str(event.get("text")).lower()
                
                is_red_card = (evt_type_code in ("red-card", "yellow-red-card") or 
                               "red card" in evt_type.get("text", "").lower() or 
                               "red card" in evt_text)
                               
                if is_red_card:
                    card_team = event.get("team", {}).get("displayName")
                    if card_team:
                        if _is_name_match(card_team, t1):
                            rc_t1 += 1
                        elif _is_name_match(card_team, t2):
                            rc_t2 += 1
                            
            if rc_t1 > 0: extra["red_card_t1"] = rc_t1
            if rc_t2 > 0: extra["red_card_t2"] = rc_t2
            
            score_det = matched_event.get("competitions", [{}])[0].get("status", {}).get("type", {})
            if "shootout" in str(score_det.get("detail", "")).lower() or score_det.get("name") == "STATUS_SHOOTOUT":
                extra["penalties"] = True
                
    except Exception as e:
        logging.error("Failed to fetch ESPN match summary %s: %s", game_id, e)

def _fetch_detailed_bookings_and_extra(api_id, t1, t2, headers, extra):
    try:
        match_url = f"{FOOTBALL_API_BASE}/matches/{api_id}"
        m_resp = requests.get(match_url, headers=headers, timeout=10)
        if m_resp.status_code == 200:
            m_det = m_resp.json()
            
            # Red cards / bookings
            rc_t1, rc_t2 = 0, 0
            bookings = m_det.get("bookings", [])
            for b in bookings:
                if b.get("type") in ("RED_CARD", "YELLOW_RED_CARD"):
                    card_team = b.get("team", {}).get("name")
                    if card_team:
                        if _is_name_match(card_team, t1):
                            rc_t1 += 1
                        elif _is_name_match(card_team, t2):
                            rc_t2 += 1
            if rc_t1 > 0: extra["red_card_t1"] = rc_t1
            if rc_t2 > 0: extra["red_card_t2"] = rc_t2
            
            # Penalty shootout
            score_det = m_det.get("score", {})
            if score_det.get("duration") == "PENALTY_SHOOTOUT":
                extra["penalties"] = True
                extra["winner"] = t1 if score_det.get("winner") == "HOME_TEAM" else t2
                
            # Hattricks
            counts = {}
            goals = m_det.get("goals", [])
            for g in goals:
                scorer = g.get("scorer", {})
                sid = scorer.get("id") or scorer.get("name")
                if sid: counts[sid] = counts.get(sid, 0) + 1
            for sid, goal_count in counts.items():
                if goal_count >= 3:
                    scorer_team = next((g["team"]["name"] for g in goals if (g.get("scorer", {}).get("id") or g.get("scorer", {}).get("name")) == sid), "")
                    if _is_name_match(scorer_team, t1): extra["hattrick_t1"] = True
                    else: extra["hattrick_t2"] = True
    except Exception as e:
        logging.error("Failed to fetch detailed match %s for bookings: %s", api_id, e)

    # ALWAYS enrich/verify from ESPN to ensure red cards sync works even on free tier!
    _fetch_detailed_bookings_and_extra_espn(t1, t2, extra)

def _match_team_names(h1, a1, h2, a2):
    return (_is_name_match(h1, h2) and _is_name_match(a1, a2)) or (_is_name_match(h1, a2) and _is_name_match(a1, h2))

def _map_stage_simple(s):
    s = str(s or "").lower()
    if "group" in s: return "group"
    if "32" in s: return "r32"
    if "16" in s: return "r16"
    if "quarter" in s: return "qf"
    if "semi" in s: return "sf"
    if "final" in s: return "final"
    return "group"

@app.route("/api/match/sync-live", methods=["POST"])
def api_match_sync_live():
    """Sync all live or finished matches from external APIs and update data."""
    data = load_data()
    # Logic to fetch and merge live results...
    # For now, we'll implement a robust sync that updates based on ANY finished matches found.
    # This endpoint can be polled by the frontend.
    headers = {"X-Auth-Token": FOOTBALL_API_KEY} if FOOTBALL_API_KEY else {}
    count = 0
    try:
        # Check Football-Data.org
        resp = requests.get(f"{FOOTBALL_API_BASE}/competitions/{WC2026_COMPETITION}/matches", headers=headers, timeout=10)
        if resp.status_code == 200:
            matches = resp.json().get("matches", [])
            recorded_ids = {str(m.get("fixture_id")) for m in data.get("matches", []) if m.get("fixture_id")}
            for m in matches:
                if m.get("status") == "FINISHED" and str(m["id"]) not in recorded_ids:
                    t1_raw, t2_raw = m["homeTeam"]["name"], m["awayTeam"]["name"]
                    t1 = next((t["name"] for t in TEAMS if _is_name_match(t["name"], t1_raw)), t1_raw)
                    t2 = next((t["name"] for t in TEAMS if _is_name_match(t["name"], t2_raw)), t2_raw)
                    
                    extra = {}
                    _fetch_detailed_bookings_and_extra(str(m["id"]), t1, t2, headers, extra)
                    if not extra.get("hattrick_t1") and not extra.get("hattrick_t2"):
                        _enrich_hattricks_from_fallback(t1, t2, extra)

                    score = _get_api_match_score(m)
                    res = _auto_record_match(data, t1, t2, score["home"], score["away"], _map_stage(m.get("stage", "")), str(m["id"]), extra)
                    if res: count += 1
        
        if count > 0: save_data(data)
        return jsonify({"ok": True, "count": count, "message": f"Synced {count} matches."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def _auto_record_match(data, t1, t2, s1, s2, stage, fixture_id, extra=None):
    if any(m.get("fixture_id") == fixture_id for m in data.get("matches", [])): return False
    extra = extra or {}
    result = score_analyser(t1, t2, s1, s2, stage, extra, pts_config=data.get("points_config"))
    o1 = data["team_sold"].get(get_official_team_name(t1))
    o2 = data["team_sold"].get(get_official_team_name(t2))
    if o1: data["points"][o1] = data["points"].get(o1, 0) + result["team1"]["points"]
    if o2: data["points"][o2] = data["points"].get(o2, 0) + result["team2"]["points"]
    match_record = {
        "id": str(uuid.uuid4())[:8], "team1": t1, "team2": t2, "score1": s1, "score2": s2,
        "stage": stage, "extra": extra, "owner1": o1, "owner2": o2, "result": result,
        "timestamp": datetime.now().strftime("%d %b %Y, %H:%M"),
        "flag1": get_team_flag(t1), "flag2": get_team_flag(t2),
        "fixture_id": fixture_id,
    }
    data["matches"].insert(0, match_record)
    return True


def fetch_all_fixtures() -> dict:
    cache_key = "fixtures|all"
    now = time.time()
    if cache_key in _fetch_cache:
        ts, payload = _fetch_cache[cache_key]
        if now - ts < CACHE_TTL:
            return payload
    headers = {"X-Auth-Token": FOOTBALL_API_KEY} if FOOTBALL_API_KEY else {}
    try:
        resp = requests.get(
            f"{FOOTBALL_API_BASE}/competitions/{WC2026_COMPETITION}/matches",
            headers=headers, timeout=10,
        )
        if resp.status_code != 200:
            result = {"fixtures": [], "error": f"API returned HTTP {resp.status_code}"}
        else:
            raw = resp.json().get("matches", [])
            fixtures = []
            for m in raw:
                utc = m.get("utcDate", "")
                try:
                    dt = datetime.strptime(utc, "%Y-%m-%dT%H:%M:%SZ")
                    display_dt = dt.strftime("%d %b %Y, %H:%M")
                except ValueError:
                    display_dt = utc
                score = _get_api_match_score(m)
                fixtures.append({
                    "id": m["id"],
                    "round": m.get("matchday") or m.get("stage", ""),
                    "stage_raw": m.get("stage", ""),
                    "status": m.get("status", ""),
                    "utc": utc,
                    "display_dt": display_dt,
                    "home": m["homeTeam"]["name"],
                    "away": m["awayTeam"]["name"],
                    "score_home": score.get("home"),
                    "score_away": score.get("away"),
                })
            result = {"fixtures": fixtures, "error": None}
    except requests.RequestException as e:
        result = {"fixtures": [], "error": str(e)}

    if not result["fixtures"]:
        static = []
        for f in WC2026_FIXTURES:
            static.append({
                "id": f"{f['home']}|{f['away']}",
                "round": f["round"],
                "stage_raw": f["stage"],
                "status": "SCHEDULED",
                "utc": "",
                "display_dt": f["date"],
                "home": f["home"],
                "away": f["away"],
                "score_home": None,
                "score_away": None,
            })
        result = {"fixtures": static, "error": result.get("error")}

    _fetch_cache[cache_key] = (now, result)
    return result


def get_public_group_fixtures() -> tuple[list[dict], Optional[str]]:
    fx = fetch_all_fixtures()
    fixtures = []
    for f in fx["fixtures"]:
        round_label = str(f.get("round", ""))
        stage_raw = str(f.get("stage_raw", ""))
        if stage_raw.upper() not in {"GROUP_STAGE", "GROUP"} and not round_label.startswith("Group"):
            continue
        fixtures.append(dict(f))

    def sort_key(item):
        utc = item.get("utc") or ""
        if utc:
            try:
                return (datetime.strptime(utc, "%Y-%m-%dT%H:%M:%SZ"), item.get("home", ""), item.get("away", ""))
            except ValueError:
                pass
        return (item.get("display_dt", ""), item.get("home", ""), item.get("away", ""))

    fixtures.sort(key=sort_key)
    return fixtures, fx["error"]


def find_public_group_fixture(fixture_id):
    if fixture_id is None:
        return None
    fixtures, _ = get_public_group_fixtures()
    fid = str(fixture_id)
    return next((f for f in fixtures if str(f.get("id")) == fid), None)


def fetch_standings() -> dict:
    cache_key = "standings|all"
    now = time.time()
    if cache_key in _fetch_cache:
        ts, payload = _fetch_cache[cache_key]
        if now - ts < CACHE_TTL:
            return payload
    headers = {"X-Auth-Token": FOOTBALL_API_KEY} if FOOTBALL_API_KEY else {}
    try:
        resp = requests.get(
            f"{FOOTBALL_API_BASE}/competitions/{WC2026_COMPETITION}/standings",
            headers=headers, timeout=10,
        )
        if resp.status_code != 200:
            result = {"groups": {}, "error": f"API returned HTTP {resp.status_code}"}
        else:
            groups = {}
            for standing in resp.json().get("standings", []):
                group_name = standing.get("group", "")
                letter = group_name.replace("GROUP_", "") if group_name else standing.get("stage", "")
                rows = []
                for entry in standing.get("table", []):
                    rows.append({
                        "position": entry["position"],
                        "team": entry["team"]["name"],
                        "played": entry["playedGames"],
                        "won": entry["won"],
                        "draw": entry["draw"],
                        "lost": entry["lost"],
                        "gf": entry["goalsFor"],
                        "ga": entry["goalsAgainst"],
                        "gd": entry["goalDifference"],
                        "pts": entry["points"],
                    })
                groups[letter] = rows
            result = {"groups": groups, "error": None}
    except requests.RequestException as e:
        result = {"groups": {}, "error": str(e)}
    _fetch_cache[cache_key] = (now, result)
    return result


def _knockout_slot_label(slot_type: str, group=None) -> str:
    if slot_type == "1st":
        return f"1st {group}"
    if slot_type == "2nd":
        return f"2nd {group}"
    if slot_type == "3rd":
        return "Best 3rd-place team"
    return "TBD"


def calculate_local_group_standings(data):
    standings = {}
    for letter, teams in WC2026_GROUPS.items():
        standings[letter] = {
            t: {"team": t, "played": 0, "won": 0, "draw": 0, "lost": 0, "gf": 0, "ga": 0, "gd": 0, "pts": 0}
            for t in teams
        }
    
    for m in data.get("matches", []):
        if m.get("stage") == "group":
            t1 = get_official_team_name(m["team1"])
            t2 = get_official_team_name(m["team2"])
            s1, s2 = int(m["score1"]), int(m["score2"])
            g1, g2 = get_team_group(t1), get_team_group(t2)
            
            if g1 and t1 in standings[g1]:
                st1 = standings[g1][t1]
                st1["played"] += 1
                st1["gf"] += s1
                st1["ga"] += s2
                st1["gd"] += (s1 - s2)
                if s1 > s2:
                    st1["won"] += 1
                    st1["pts"] += 3
                elif s1 == s2:
                    st1["draw"] += 1
                    st1["pts"] += 1
                else:
                    st1["lost"] += 1
                    
            if g2 and t2 in standings[g2]:
                st2 = standings[g2][t2]
                st2["played"] += 1
                st2["gf"] += s2
                st2["ga"] += s1
                st2["gd"] += (s2 - s1)
                if s2 > s1:
                    st2["won"] += 1
                    st2["pts"] += 3
                elif s1 == s2:
                    st2["draw"] += 1
                    st2["pts"] += 1
                else:
                    st2["lost"] += 1
                    
    sorted_groups = {}
    for letter, teams_dict in standings.items():
        sorted_teams = sorted(
            teams_dict.values(),
            key=lambda x: (-x["pts"], -x["gd"], -x["gf"], x["team"])
        )
        for i, t in enumerate(sorted_teams):
            t["position"] = i + 1
        sorted_groups[letter] = sorted_teams
    return sorted_groups


def assign_3rds(slots, teams, current_assignment=None):
    if current_assignment is None:
        current_assignment = {}
    if not slots:
        return current_assignment
    
    slot_match, winner_group = slots[0]
    for i, (team_name, team_group) in enumerate(teams):
        if team_group != winner_group:
            remaining_teams = teams[:i] + teams[i+1:]
            new_assignment = current_assignment.copy()
            new_assignment[slot_match] = team_name
            res = assign_3rds(slots[1:], remaining_teams, new_assignment)
            if res:
                return res
    return None


def _get_team_group_pts(team_name, sorted_groups):
    for group, table in sorted_groups.items():
        for t in table:
            if t["team"] == team_name:
                return t["pts"], t["gd"], t["gf"]
    return 0, 0, 0


def resolve_match_outcome(match_num, data, sorted_groups, assigned_3rds, resolved_cache):
    if match_num in resolved_cache:
        return resolved_cache[match_num]
        
    by_num = {m.get("match_num"): m for m in data.get("matches", []) if m.get("match_num")}
    record = by_num.get(match_num)
    
    if record:
        team1 = record["team1"]
        team2 = record["team2"]
        score1 = record["score1"]
        score2 = record["score2"]
        res = record.get("result", {})
        
        is_winner1 = False
        if res:
            is_winner1 = (score1 > score2) or (score1 == score2 and record.get("extra", {}).get("winner") == team1)
            if score1 == score2 and not record.get("extra", {}).get("winner"):
                is_winner1 = res.get("team1", {}).get("points", 0) > res.get("team2", {}).get("points", 0)
                
        winner = team1 if is_winner1 else team2
        loser = team2 if is_winner1 else team1
        outcome = {"team1": team1, "team2": team2, "winner": winner, "loser": loser, "played": True}
        resolved_cache[match_num] = outcome
        return outcome
        
    if match_num <= 88:
        actual_teams = WC2026_R32_ACTUAL_TEAMS.get(match_num)
        if actual_teams:
            team1, team2 = actual_teams
        else:
            team1, team2 = "TBD", "TBD"
    else:
        BRACKET_TREE = {
            89: {"type": "winner", "a": 74, "b": 77},
            90: {"type": "winner", "a": 73, "b": 75},
            91: {"type": "winner", "a": 76, "b": 78},
            92: {"type": "winner", "a": 79, "b": 80},
            93: {"type": "winner", "a": 83, "b": 84},
            94: {"type": "winner", "a": 81, "b": 82},
            95: {"type": "winner", "a": 86, "b": 88},
            96: {"type": "winner", "a": 85, "b": 87},
            
            97: {"type": "winner", "a": 89, "b": 90},
            98: {"type": "winner", "a": 93, "b": 94},
            99: {"type": "winner", "a": 91, "b": 92},
            100: {"type": "winner", "a": 95, "b": 96},
            
            101: {"type": "winner", "a": 97, "b": 98},
            102: {"type": "winner", "a": 99, "b": 100},
            
            103: {"type": "loser", "a": 101, "b": 102},
            104: {"type": "winner", "a": 101, "b": 102}
        }
        cfg = BRACKET_TREE.get(match_num)
        if cfg:
            res_a = resolve_match_outcome(cfg["a"], data, sorted_groups, assigned_3rds, resolved_cache)
            res_b = resolve_match_outcome(cfg["b"], data, sorted_groups, assigned_3rds, resolved_cache)
            if cfg["type"] == "winner":
                team1, team2 = res_a["winner"], res_b["winner"]
            else:
                team1, team2 = res_a["loser"], res_b["loser"]
        else:
            team1, team2 = "TBD", "TBD"

    # Fallback team matching check: if a match exists in database between team1 and team2 in knockout stages
    if team1 != "TBD" and team2 != "TBD":
        norm_t1 = normalize_team_name(team1)
        norm_t2 = normalize_team_name(team2)
        for m in data.get("matches", []):
            if m.get("stage") != "group":
                mt1, mt2 = m.get("team1"), m.get("team2")
                norm_mt1 = normalize_team_name(mt1)
                norm_mt2 = normalize_team_name(mt2)
                if (norm_mt1 == norm_t1 and norm_mt2 == norm_t2) or (norm_mt1 == norm_t2 and norm_mt2 == norm_t1):
                    score1 = m["score1"]
                    score2 = m["score2"]
                    res = m.get("result", {})
                    
                    rec_winner = None
                    if score1 > score2:
                        rec_winner = mt1
                    elif score2 > score1:
                        rec_winner = mt2
                    elif m.get("extra", {}).get("winner"):
                        rec_winner = m["extra"]["winner"]
                    else:
                        rec_winner = mt1 if res.get("team1", {}).get("points", 0) > res.get("team2", {}).get("points", 0) else mt2
                        
                    is_winner_team1 = (normalize_team_name(rec_winner) == norm_t1)
                    winner = team1 if is_winner_team1 else team2
                    loser = team2 if is_winner_team1 else team1
                    outcome = {"team1": team1, "team2": team2, "winner": winner, "loser": loser, "played": True}
                    resolved_cache[match_num] = outcome
                    return outcome
            
    if team1 == "TBD" and team2 == "TBD":
        winner, loser = "TBD", "TBD"
    elif team1 == "TBD":
        winner, loser = team2, "TBD"
    elif team2 == "TBD":
        winner, loser = team1, "TBD"
    else:
        pts1, gd1, gf1 = _get_team_group_pts(team1, sorted_groups)
        pts2, gd2, gf2 = _get_team_group_pts(team2, sorted_groups)
        if (pts1, gd1, gf1) >= (pts2, gd2, gf2):
            winner, loser = team1, team2
        else:
            winner, loser = team2, team1
            
    outcome = {"team1": team1, "team2": team2, "winner": winner, "loser": loser, "played": False}
    resolved_cache[match_num] = outcome
    return outcome


def build_knockout_sections(data: dict) -> list[dict]:
    sorted_groups = calculate_local_group_standings(data)
    
    thirds = []
    for l in "ABCDEFGHIJKL":
        if l in sorted_groups and len(sorted_groups[l]) >= 3:
            thirds.append(sorted_groups[l][2])
            
    sorted_thirds = sorted(thirds, key=lambda x: (-x["pts"], -x["gd"], -x["gf"], x["team"]))
    q_3rds = [(t["team"], get_team_group(t["team"])) for t in sorted_thirds[:8]]
    
    slots_3rd = [
        (74, "E"), (77, "I"), (79, "A"), (80, "L"),
        (81, "D"), (82, "G"), (85, "B"), (87, "K")
    ]
    assigned_3rds = assign_3rds(slots_3rd, q_3rds)
    if not assigned_3rds:
        assigned_3rds = {match_num: q_3rds[i][0] for i, (match_num, _) in enumerate(slots_3rd) if i < len(q_3rds)}
        
    resolved_cache = {}
    for match_num in range(73, 105):
        resolve_match_outcome(match_num, data, sorted_groups, assigned_3rds, resolved_cache)
        
    matches_list = data.get("matches", [])
    by_num = {m.get("match_num"): m for m in matches_list if m.get("match_num")}
    
    def resolve_record(match_num: int):
        rec = by_num.get(match_num)
        if rec:
            return rec
        pred = resolved_cache.get(match_num)
        if not pred or pred.get("team1") == "TBD" or pred.get("team2") == "TBD":
            return None
        t1, t2 = pred["team1"], pred["team2"]
        norm1, norm2 = normalize_team_name(t1), normalize_team_name(t2)
        for m in matches_list:
            if m.get("stage") != "group":
                mt1, mt2 = m.get("team1"), m.get("team2")
                norm_mt1 = normalize_team_name(mt1)
                norm_mt2 = normalize_team_name(mt2)
                if (norm_mt1 == norm1 and norm_mt2 == norm2) or (norm_mt1 == norm2 and norm_mt2 == norm1):
                    return m
        return None
        
    sections = []

    r32_items = []
    for slot in WC2026_R32_BRACKET:
        m_num = slot["match"]
        rec = resolve_record(m_num)
        pred = resolved_cache.get(m_num, {})
        r32_items.append({
            "match_num": m_num,
            "date": slot["date"],
            "left_label": _knockout_slot_label(slot["slot_a"][0], slot["slot_a"][1]),
            "right_label": _knockout_slot_label(slot["slot_b"][0], slot["slot_b"][1]),
            "record": rec,
            "predicted_team1": pred.get("team1") if pred.get("team1") != "TBD" else None,
            "predicted_team2": pred.get("team2") if pred.get("team2") != "TBD" else None,
            "badge": "Round of 32",
        })
    sections.append({"title": "Round of 32", "matches": r32_items})

    r16_items = []
    for slot in WC2026_R16_BRACKET:
        m_num = slot["match"]
        rec = resolve_record(m_num)
        pred = resolved_cache.get(m_num, {})
        r16_items.append({
            "match_num": m_num,
            "date": slot["date"],
            "left_label": f"Winner of Match {slot['r32_a']}",
            "right_label": f"Winner of Match {slot['r32_b']}",
            "record": rec,
            "predicted_team1": pred.get("team1") if pred.get("team1") != "TBD" else None,
            "predicted_team2": pred.get("team2") if pred.get("team2") != "TBD" else None,
            "badge": "Round of 16",
        })
    sections.append({"title": "Round of 16", "matches": r16_items})

    qf_refs = [(97, 89, 90), (98, 93, 94), (99, 91, 92), (100, 95, 96)]
    qf_items = []
    for m_num, a, b in qf_refs:
        rec = resolve_record(m_num)
        pred = resolved_cache.get(m_num, {})
        qf_items.append({
            "match_num": m_num,
            "date": "",
            "left_label": f"Winner of Match {a}",
            "right_label": f"Winner of Match {b}",
            "record": rec,
            "predicted_team1": pred.get("team1") if pred.get("team1") != "TBD" else None,
            "predicted_team2": pred.get("team2") if pred.get("team2") != "TBD" else None,
            "badge": "Quarter-final",
        })
    sections.append({"title": "Quarter-finals", "matches": qf_items})

    sf_refs = [(101, 97, 98), (102, 99, 100)]
    sf_items = []
    for m_num, a, b in sf_refs:
        rec = resolve_record(m_num)
        pred = resolved_cache.get(m_num, {})
        sf_items.append({
            "match_num": m_num,
            "date": "",
            "left_label": f"Winner of Match {a}",
            "right_label": f"Winner of Match {b}",
            "record": rec,
            "predicted_team1": pred.get("team1") if pred.get("team1") != "TBD" else None,
            "predicted_team2": pred.get("team2") if pred.get("team2") != "TBD" else None,
            "badge": "Semi-final",
        })
    sections.append({"title": "Semi-finals", "matches": sf_items})

    third_rec = resolve_record(103)
    pred_third = resolved_cache.get(103, {})
    sections.append({
        "title": "Third-place playoff",
        "matches": [{
            "match_num": 103,
            "date": "",
            "left_label": "Loser of Match 101",
            "right_label": "Loser of Match 102",
            "record": third_rec,
            "predicted_team1": pred_third.get("team1") if pred_third.get("team1") != "TBD" else None,
            "predicted_team2": pred_third.get("team2") if pred_third.get("team2") != "TBD" else None,
            "badge": "No fantasy points",
            "no_points": True,
        }],
    })
    
    final_rec = resolve_record(104)
    pred_final = resolved_cache.get(104, {})
    sections.append({
        "title": "Final",
        "matches": [{
            "match_num": 104,
            "date": "",
            "left_label": "Winner of Match 101",
            "right_label": "Winner of Match 102",
            "record": final_rec,
            "predicted_team1": pred_final.get("team1") if pred_final.get("team1") != "TBD" else None,
            "predicted_team2": pred_final.get("team2") if pred_final.get("team2") != "TBD" else None,
            "badge": "Championship",
        }],
    })
    return sections


def is_team_still_in(team_name, data):
    # Check if they lost a knockout match in data["matches"]
    for m in data.get("matches", []):
        if m.get("stage") != "group":
            if m.get("team1") == team_name or m.get("team2") == team_name:
                s1, s2 = m.get("score1"), m.get("score2")
                if s1 is not None and s2 is not None:
                    if s1 == s2:
                        winner = m.get("extra", {}).get("winner")
                        if winner and winner != team_name:
                            return False
                    else:
                        if m.get("team1") == team_name and s1 < s2:
                            return False
                        if m.get("team2") == team_name and s2 < s1:
                            return False

    # Check if they qualified for R32
    r32_teams = set()
    for t_pair in WC2026_R32_ACTUAL_TEAMS.values():
        r32_teams.add(t_pair[0])
        r32_teams.add(t_pair[1])
    
    if r32_teams:
        if team_name not in r32_teams:
            return False
            
    return True

def build_team_point_rows(data: dict) -> list[dict]:
    rows = []
    matches = data.get("matches", [])
    tiers = data.get("tiers", {})
    for player in data.get("players", []):
        name = player["name"]
        owned = data.get("ownership", {}).get(name, [])
        teams = []
        for team_name in owned:
            team_pts = 0
            for m in matches:
                if m.get("owner1") == name and m.get("team1") == team_name:
                    team_pts += m.get("result", {}).get("team1", {}).get("points", 0)
                if m.get("owner2") == name and m.get("team2") == team_name:
                    team_pts += m.get("result", {}).get("team2", {}).get("points", 0)
            team_obj = next((t for t in TEAMS if t["name"] == team_name), {"flag": "🏳"})
            group = get_team_group(team_name)
            teams.append({
                "name": team_name,
                "flag": team_obj.get("flag", "🏳"),
                "tier": get_team_tier(team_name, tiers),
                "group": group,
                "group_label": f"Group {group}" if group else None,
                "points": team_pts,
                "is_still_in": is_team_still_in(team_name, data),
            })
        teams.sort(key=lambda r: (-r["points"], r["name"]))
        active_teams = [t for t in teams if t["is_still_in"]]
        rows.append({
            "name": name,
            "pts": data.get("points", {}).get(name, 0),
            "owned": owned,
            "teams": teams,
            "team_points": sum(t["points"] for t in teams),
            "matches_played": sum(1 for m in matches if m.get("owner1") == name or m.get("owner2") == name),
            "active_teams_count": len(active_teams),
            "eliminated_teams_count": len(teams) - len(active_teams),
        })
    rows.sort(key=lambda r: (-r["pts"], r["name"]))
    return rows


def validate_match_input(body: dict):
    t1 = body.get("team1", "")
    t2 = body.get("team2", "")
    if not t1 or t1 not in TEAM_NAMES:
        return f"team1 '{t1}' is not a recognised team"
    if not t2 or t2 not in TEAM_NAMES:
        return f"team2 '{t2}' is not a recognised team"
    try:
        s1, s2 = int(body["score1"]), int(body["score2"])
    except (KeyError, ValueError, TypeError):
        return "score1 and score2 must be integers"
    if not (0 <= s1 <= 20 and 0 <= s2 <= 20):
        return "scores must be in range 0-20"
    if body.get("stage", "group") not in VALID_STAGES:
        return f"stage must be one of {sorted(VALID_STAGES)}"
    fixture_id = body.get("fixture_id")
    if fixture_id:
        fixture = find_public_group_fixture(fixture_id)
        if not fixture:
            return "fixture_id is not recognised"
        if body.get("stage", "group") != "group":
            return "public fixture matches must be recorded as group stage"
        if fixture.get("home") != t1 or fixture.get("away") != t2:
            return "selected fixture teams do not match the public schedule"

    extra = body.get("extra", {})
    if extra and extra.get("penalties"):
        if body.get("stage", "group") == "group":
            return "penalty shootouts cannot occur in the group stage"
        if s1 != s2:
            return "matches won on penalties must end in a draw at full time (e.g. 1-1)"
        winner = extra.get("winner")
        if not winner or winner not in (t1, t2):
            return "shootout winner must be one of the playing teams"
    return None

def validate_players(players: list):
    if not (2 <= len(players) <= 10):
        return "between 2 and 10 players required"
    for p in players:
        if not p or not isinstance(p, str) or len(p.strip()) == 0:
            return "player names must be non-empty strings"
        if len(p.strip()) > 50:
            return "player names must be at most 50 characters"
    return None

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_authed"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    warn_default = (ADMIN_PIN == "1234")
    if request.method == "POST":
        if request.form.get("pin") == ADMIN_PIN:
            session["admin_authed"] = True
            return redirect(url_for("admin"))
        error = "Incorrect PIN"
    return render_template("admin_login.html", error=error, warn_default=warn_default, data=load_data())

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_authed", None)
    return redirect(url_for("admin_login"))

@app.route("/admin")
@admin_required
def admin():
    data = load_data()
    public_group_fixtures, public_fixtures_error = get_public_group_fixtures()
    return render_template("admin.html", data=data, teams=TEAMS,
                           default_tiers=DEFAULT_TIERS, points_defaults=POINTS_DEFAULTS,
                           teams_per_player=get_teams_per_player(data),
                           public_group_fixtures=public_group_fixtures,
                           public_fixtures_error=public_fixtures_error,
                           active_page="admin")

def get_dashboard_data(data):
    players = [p["name"] for p in data.get("players", [])]
    if not players:
        return {}
        
    fixture_matchday_map = {}
    group_counts = {}
    for f in WC2026_FIXTURES:
        g = f.get("group")
        group_counts[g] = group_counts.get(g, 0) + 1
        idx = group_counts[g]
        if idx <= 2:
            md = "MD1"
        elif idx <= 4:
            md = "MD2"
        else:
            md = "MD3"
        h = normalize_team_name(f["home"])
        a = normalize_team_name(f["away"])
        fixture_matchday_map[(h, a)] = md
        fixture_matchday_map[(a, h)] = md

    rounds = ["MD1", "MD2", "MD3", "R032", "R016", "QF", "SF", "FINAL"]
    round_points = {p: {r: 0 for r in rounds} for p in players}
    played_rounds = set()
    
    for m in data.get("matches", []):
        stage = m.get("stage")
        if stage == "group":
            h = normalize_team_name(m["team1"])
            a = normalize_team_name(m["team2"])
            r_label = fixture_matchday_map.get((h, a), "MD1")
        elif stage == "r32":
            r_label = "R032"
        elif stage == "r16":
            r_label = "R016"
        elif stage == "qf":
            r_label = "QF"
        elif stage == "sf":
            r_label = "SF"
        elif stage == "final":
            r_label = "FINAL"
        else:
            continue
            
        res = m.get("result", {})
        if res:
            played_rounds.add(r_label)
            o1, o2 = m.get("owner1"), m.get("owner2")
            if o1 in round_points:
                round_points[o1][r_label] += res.get("team1", {}).get("points", 0)
            if o2 in round_points:
                round_points[o2][r_label] += res.get("team2", {}).get("points", 0)

    if not played_rounds:
        played_rounds.add("MD1")
        
    active_round = "MD1"
    for r in rounds:
        if r in played_rounds:
            active_round = r
            
    cumulative = {p: {} for p in players}
    for p in players:
        curr_total = 0
        for r in rounds:
            curr_total += round_points[p][r]
            cumulative[p][r] = curr_total
            
    ranks = {p: {} for p in players}
    for r in rounds:
        sorted_players = sorted(players, key=lambda p: (cumulative[p][r], p), reverse=True)
        curr_rank = 1
        for idx, player in enumerate(sorted_players):
            if idx > 0:
                prev_player = sorted_players[idx-1]
                if cumulative[player][r] < cumulative[prev_player][r]:
                    curr_rank = idx + 1
            ranks[player][r] = curr_rank

    payload = {
        "rounds": rounds,
        "players": players,
        "active_round": active_round,
        "played_rounds": list(played_rounds),
        "round_points": round_points,
        "cumulative": cumulative,
        "ranks": ranks,
        "colors": {p: get_player_color(p) for p in players},
    }
    return payload


@app.route("/")
def index():
    data = load_data()
    player_teams_by_group = {}
    player_matches = {}
    if data.get("players"):
        for player in data["players"]:
            player_name = player["name"]
            player_teams_by_group[player_name] = get_player_teams_by_group(player_name, data)
            player_matches[player_name] = 0

    for m in data.get("matches", []):
        o1, o2 = m.get("owner1"), m.get("owner2")
        if o1 in player_matches: player_matches[o1] += 1
        if o2 in player_matches: player_matches[o2] += 1

    fx_data = fetch_all_fixtures()
    next_match = get_next_match(fx_data)
    
    dashboard_data = get_dashboard_data(data)

    return render_template(
        "index.html",
        data=data,
        teams=TEAMS,
        active_page="home",
        player_teams_by_group=player_teams_by_group,
        player_matches=player_matches,
        next_match=next_match,
        get_player_color=get_player_color,
        dashboard_json=json.dumps(dashboard_data)
    )

@app.route("/how-to-play")
def how_to_play():
    data = load_data()
    pts = data.get("points_config") or POINTS_DEFAULTS
    return render_template("how_to_play.html", data=data, pts=pts, teams=TEAMS, active_page="how-to-play", get_player_color=get_player_color)

@app.route("/api/data")
def api_data():
    return jsonify(load_data())

@app.route("/api/setup", methods=["POST"])
def api_setup():
    data = load_data()
    body = request.json
    players = body.get("players", [])
    err = validate_players(players)
    if err:
        return jsonify({"error": err}), 400
    tpp_raw = body.get("teams_per_player", 0)
    try:
        tpp = int(tpp_raw)
    except (ValueError, TypeError):
        return jsonify({"error": "teams_per_player must be a number"}), 400
    if tpp < 0:
        return jsonify({"error": "teams_per_player must be 0 (auto) or a positive number"}), 400
    data["league_name"] = body.get("league_name", "WC2026 Fantasy")
    try:
        data["budget"] = int(body.get("budget", 1000))
    except (TypeError, ValueError):
        return jsonify({"error": "budget must be a whole number"}), 400
    data["players"] = [{"name": n} for n in players if n.strip()]
    data["teams_per_player"] = tpp
    save_data(data)
    return jsonify({"ok": True, "teams_per_player": get_teams_per_player(data)})

@app.route("/api/tiers", methods=["POST"])
def api_tiers():
    data = load_data()
    body = request.json
    tiers_payload = body.get("tiers", DEFAULT_TIERS)
    data["tiers"] = {str(k): list(v) for k, v in tiers_payload.items()}
    try:
        data["tier_prices"] = {str(k): int(v) for k, v in body.get("tier_prices", {}).items()}
    except (TypeError, ValueError):
        return jsonify({"error": "tier prices must be whole numbers"}), 400
    data["budgets"] = {p["name"]: data["budget"] for p in data["players"]}
    data["points"] = {p["name"]: 0 for p in data["players"]}
    data["ownership"] = {}
    data["team_sold"] = {}
    data["auction_queue"] = build_group_order_auction_queue(data["tiers"])
    data["auction_idx"] = 0
    data["current_bidder"] = 0
    data["current_bid"] = 0
    data["current_high_bidder"] = None
    data["auction_active_bidders"] = []
    data["auction_active_team"] = None
    data["started"] = True
    data["auction_done"] = False
    save_data(data)
    return jsonify({"ok": True})

@app.route("/api/auction/bid", methods=["POST"])
def api_bid():
    data = load_data()
    body = request.json
    if data["auction_done"] or data["auction_idx"] >= len(data["auction_queue"]):
        return jsonify({"ok": False, "error": "Auction over"})
    team_name = data["auction_queue"][data["auction_idx"]]
    tier = get_team_tier(team_name, data["tiers"])
    base = data["tier_prices"].get(str(tier), 40)
    min_bid = _current_auction_min_bid(data, base)
    players = data["players"]
    cap = get_teams_per_player(data)
    bidder_idx = _resolve_bidder_index(data, body.get("bidder"))
    data["current_bidder"] = bidder_idx
    if not _advance_past_ineligible_bidder(data, team_name, cap, min_bid):
        save_data(data)
        return jsonify({"ok": True, "data": data})
    cp_idx = data["current_bidder"]
    cp = players[cp_idx]["name"]
    at_cap = len(data.get("ownership", {}).get(cp, [])) >= cap
    no_budget = data["budgets"].get(cp, 0) < min_bid
    if at_cap or no_budget:
        next_b = _next_eligible_bidder(data, (cp_idx + 1) % len(players), cap, min_bid)
        data["current_bidder"] = next_b
        if next_b == cp_idx:
            _finalize_current_team(data, team_name, base)
        save_data(data)
        return jsonify({"ok": False, "error": f"{cp} skipped", "data": data})
    amt = int(body.get("amount", base))
    if amt < min_bid:
        return jsonify({"ok": False, "error": f"Min bid is {min_bid}"})
    if amt > data["budgets"].get(cp, 0):
        return jsonify({"ok": False, "error": f"{cp} only has {data['budgets'].get(cp,0)} points"})
    data["current_bid"] = amt
    data["current_high_bidder"] = cp
    next_b = _next_eligible_bidder(data, (cp_idx + 1) % len(players), cap, min_bid)
    data["current_bidder"] = next_b
    if next_b == players.index(next((p for p in players if p["name"] == data["current_high_bidder"]), players[0])):
        _finalize_current_team(data, team_name, base)
    save_data(data)
    return jsonify({"ok": True, "data": data})

@app.route("/api/auction/pass", methods=["POST"])
def api_pass():
    data = load_data()
    if data["auction_done"]: return jsonify({"ok": False, "error": "Auction over"})
    team_name = data["auction_queue"][data["auction_idx"]]
    tier = get_team_tier(team_name, data["tiers"])
    base = data["tier_prices"].get(str(tier), 40)
    min_bid = _current_auction_min_bid(data, base)
    cap = get_teams_per_player(data)
    bidder_name = (request.json or {}).get("bidder") if request.is_json else None
    cp_idx = _resolve_bidder_index(data, bidder_name)
    data["current_bidder"] = cp_idx
    if not _advance_past_ineligible_bidder(data, team_name, cap, min_bid):
        save_data(data)
        return jsonify({"ok": True, "data": data})
    next_b = _next_eligible_bidder(data, (data["current_bidder"] + 1) % len(data["players"]), cap, min_bid)
    data["current_bidder"] = next_b
    high_bidder = data.get("current_high_bidder")
    if high_bidder:
        high_idx = next((i for i, p in enumerate(data["players"]) if p["name"] == high_bidder), -1)
        if next_b == high_idx:
            _finalize_current_team(data, team_name, base)
    else:
        data["auction_idx"] += 1
        data["current_bid"] = 0
        data["current_high_bidder"] = None
        data["current_bidder"] = data["auction_idx"] % max(len(data["players"]), 1)
        if data["auction_idx"] >= len(data["auction_queue"]):
            data["auction_done"] = True
    save_data(data)
    return jsonify({"ok": True, "data": data})

def _current_auction_min_bid(data, base_price: int) -> int:
    current_bid = int(data.get("current_bid", 0) or 0)
    return current_bid + 10 if current_bid > 0 else 1

def _resolve_bidder_index(data, bidder_name):
    players = data.get("players", [])
    if bidder_name:
        for idx, player in enumerate(players):
            if player.get("name") == bidder_name: return idx
    return data.get("current_bidder", 0) % max(len(players), 1)

def _advance_past_ineligible_bidder(data, team_name, cap, min_bid):
    players = data["players"]
    if not players: return False
    current_high = data.get("current_high_bidder")
    current_idx = data.get("current_bidder", 0)
    current_name = players[current_idx % len(players)]["name"]
    if current_high and current_name == current_high: return True
    current_under_cap = len(data.get("ownership", {}).get(current_name, [])) < cap
    current_can_afford = data["budgets"].get(current_name, 0) >= min_bid
    if current_under_cap and current_can_afford: return True
    next_b = _next_eligible_bidder(data, (current_idx + 1) % len(players), cap, min_bid)
    if next_b != current_idx:
        data["current_bidder"] = next_b
        return True
    team_base = data["tier_prices"].get(str(get_team_tier(team_name, data["tiers"])), 40)
    if current_high: _finalize_current_team(data, team_name, team_base)
    else:
        data["auction_idx"] += 1
        data["current_bid"] = 0
        data["current_high_bidder"] = None
        data["current_bidder"] = data["auction_idx"] % max(len(players), 1)
        if data["auction_idx"] >= len(data["auction_queue"]): data["auction_done"] = True
    return False

def _next_eligible_bidder(data, start_idx, cap, min_bid):
    players = data["players"]
    n = len(players)
    if n == 0: return 0
    for i in range(n):
        idx = (start_idx + i) % n
        name = players[idx]["name"]
        if len(data.get("ownership", {}).get(name, [])) < cap and data["budgets"].get(name, 0) >= min_bid:
            return idx
    return start_idx

def _finalize_current_team(data, team_name, base_price):
    cap = get_teams_per_player(data)
    high_bidder = data.get("current_high_bidder")
    bid_amt = data.get("current_bid", base_price)
    if high_bidder and len(data.get("ownership", {}).get(high_bidder, [])) < cap:
        _finalize_current_team_with_winner(data, team_name, high_bidder, bid_amt)
    else:
        data["auction_idx"] += 1
        data["current_bid"] = 0
        data["current_high_bidder"] = None
        data["current_bidder"] = data["auction_idx"] % max(len(data["players"]), 1)
        if data["auction_idx"] >= len(data["auction_queue"]): data["auction_done"] = True

def _finalize_current_team_with_winner(data, team_name, winner, amt):
    data["team_sold"][team_name] = winner
    if winner not in data["ownership"]: data["ownership"][winner] = []
    data["ownership"][winner].append(team_name)
    data["budgets"][winner] = max(0, data["budgets"].get(winner, 0) - amt)
    data["auction_idx"] += 1
    data["current_bid"] = 0
    data["current_high_bidder"] = None
    data["current_bidder"] = data["auction_idx"] % max(len(data["players"]), 1)
    if data["auction_idx"] >= len(data["auction_queue"]): data["auction_done"] = True

@app.route("/api/auction/auto", methods=["POST"])
def api_auto():
    data = load_data()
    queue = data["auction_queue"]
    while data["auction_idx"] < len(queue):
        team_name = queue[data["auction_idx"]]
        tier = get_team_tier(team_name, data["tiers"])
        base = data["tier_prices"].get(str(tier), 40)
        _finalize_current_team(data, team_name, base)
    data["auction_done"] = True
    save_data(data)
    return jsonify({"ok": True, "data": data})

def get_teams_per_player(data):
    explicit = data.get("teams_per_player", 0)
    if explicit and int(explicit) > 0: return int(explicit)
    n = max(len(data.get("players", [])), 1)
    return max(1, 48 // n)

@app.route("/api/match/add", methods=["POST"])
def api_match_add():
    data = load_data()
    body = request.json
    err = validate_match_input(body)
    if err: return jsonify({"error": err}), 400
    t1, t2 = body["team1"], body["team2"]
    s1, s2 = int(body["score1"]), int(body["score2"])
    stage = body.get("stage", "group")
    extra = body.get("extra", {})
    fixture_id = body.get("fixture_id")
    fixture = find_public_group_fixture(fixture_id) if fixture_id else None
    result = score_analyser(t1, t2, s1, s2, stage, extra, pts_config=data.get("points_config"))
    o1 = data["team_sold"].get(get_official_team_name(t1))
    o2 = data["team_sold"].get(get_official_team_name(t2))
    if o1: data["points"][o1] = data["points"].get(o1, 0) + result["team1"]["points"]
    if o2: data["points"][o2] = data["points"].get(o2, 0) + result["team2"]["points"]
    match_record = {
        "id": str(uuid.uuid4())[:8], "team1": t1, "team2": t2, "score1": s1, "score2": s2,
        "stage": stage, "extra": extra, "owner1": o1, "owner2": o2, "result": result,
        "timestamp": datetime.now().strftime("%d %b %Y, %H:%M"),
        "flag1": get_team_flag(t1), "flag2": get_team_flag(t2),
        "fixture_id": fixture_id, "fixture_round": fixture.get("round") if fixture else None,
        "fixture_date": fixture.get("display_dt") if fixture else None,
    }
    data["matches"].insert(0, match_record)
    save_data(data)
    return jsonify({"ok": True, "match": match_record, "data": data})

@app.route("/api/match/fetch", methods=["POST"])
def api_match_fetch():
    body = request.json or {}
    t1, t2 = body.get("team1", "").strip(), body.get("team2", "").strip()
    if not t1 or not t2: return jsonify({"error": "team1 and team2 required"}), 400
    return jsonify(fetch_match_result(t1, t2))

@app.route("/api/match/<match_id>", methods=["DELETE"])
def api_match_delete(match_id):
    data = load_data()
    match = next((m for m in data["matches"] if m["id"] == match_id), None)
    if not match: return jsonify({"error": "Match not found"}), 404
    o1, o2 = match.get("owner1"), match.get("owner2")
    if o1: data["points"][o1] = max(0, data["points"].get(o1, 0) - match["result"]["team1"]["points"])
    if o2: data["points"][o2] = max(0, data["points"].get(o2, 0) - match["result"]["team2"]["points"])
    data["matches"] = [m for m in data["matches"] if m["id"] != match_id]
    save_data(data)
    return jsonify({"ok": True})

def score_analyser(t1, t2, s1, s2, stage, extra=None, pts_config=None):
    extra, cfg = extra or {}, pts_config or POINTS_DEFAULTS
    if extra.get("third_place"):
        zero = {"name": t1, "points": 0, "breakdown": [{"event": "Third-place playoff (no pts)", "pts": 0}]}
        zero2 = {"name": t2, "points": 0, "breakdown": [{"event": "Third-place playoff (no pts)", "pts": 0}]}
        return {"team1": zero, "team2": zero2, "summary": f"{t1} {s1}-{s2} {t2} (3rd place)"}

    wb = int(cfg["win"].get(stage, 6))
    
    # Determine winner/loser correctly for knockouts (handling penalties)
    is_knockout = stage != "group"
    won1 = s1 > s2
    won2 = s2 > s1
    drew = s1 == s2
    
    if is_knockout and drew:
        if extra.get("penalties"):
            # We assume the user marked who won on penalties if they didn't provide a winning score
            # In our system, if it's a draw in knockout, 'penalties' flag usually means team1 won?
            # Actually, the UI doesn't specify who won. Let's assume if score1 == score2 and knockout:
            # The winner must be explicitly provided by slightly higher score or we check extra.
            pass

    def build(gf, ga, won, is_winner, drew, name, penalties, red_cards, hattrick):
        bd, pts = [], 0
        if is_winner:
            bd.append({"event": f"Win ({stage.upper()})", "pts": wb})
            pts += wb
        elif drew and stage == "group":
            draw_val = int(cfg.get("draw", 2))
            bd.append({"event": "Draw", "pts": draw_val})
            pts += draw_val
        else:
            loss_val = int(cfg.get("loss", 0))
            bd.append({"event": "Loss", "pts": loss_val})
            pts += loss_val

        if gf > 0:
            gp = gf * int(cfg.get("goal", 1))
            bd.append({"event": f"Goals scored ({gf})", "pts": gp})
            pts += gp
            
        if ga == 0 and (is_winner or drew):
            cs_val = int(cfg.get("clean_sheet", 2))
            bd.append({"event": "Clean sheet", "pts": cs_val})
            pts += cs_val
            
        if penalties:
            pen_val = int(cfg.get("penalties", 2))
            bd.append({"event": "Won on penalties", "pts": pen_val})
            pts += pen_val
            
        if red_cards > 0:
            rc_val = int(cfg.get("red_card", -1))
            if rc_val > 0:
                rc_val = -rc_val
            p = rc_val * red_cards
            bd.append({"event": f"Red cards ({red_cards})", "pts": p})
            pts += p
            
        if hattrick:
            hat_val = int(cfg.get("hattrick", 3))
            bd.append({"event": "Hat-trick", "pts": hat_val})
            pts += hat_val
            
        return {"name": name, "points": pts, "breakdown": bd}

    # For knockout draws, 'extra.penalties' currently doesn't say WHO won.
    # Let's check if the caller provided 'winner' in extra.
    winner_name = extra.get("winner")
    
    is_winner1 = won1 or (drew and is_knockout and winner_name == t1)
    is_winner2 = won2 or (drew and is_knockout and winner_name == t2)
    
    # If it's a knockout draw and no winner specified, fallback to whoever was marked as having 'penalties'
    # but we need to know WHICH team.
    
    r1 = build(s1, s2, won1, is_winner1, drew, t1, extra.get("penalties") and is_winner1, extra.get("red_card_t1", 0), extra.get("hattrick_t1", False))
    r2 = build(s2, s1, won2, is_winner2, drew, t2, extra.get("penalties") and is_winner2, extra.get("red_card_t2", 0), extra.get("hattrick_t2", False))
    
    return {"team1": r1, "team2": r2, "summary": f"{t1} {s1}–{s2} {t2} ({stage})"}

@app.route("/api/points", methods=["POST"])
def api_points():
    data = load_data()
    pts = (request.json or {}).get("points", {})
    data["points_config"] = pts
    save_data(data)
    return jsonify({"ok": True})

@app.route("/api/reset", methods=["POST"])
def api_reset():
    if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
    return jsonify({"ok": True})

@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    return jsonify({"error": "Simulation is disabled as the World Cup has started."}), 403

@app.route("/api/simulate-current", methods=["POST"])
def api_simulate_current():
    return jsonify({"error": "Simulation is disabled as the World Cup has started."}), 403

@app.route("/api/simulate-knockout", methods=["POST"])
def api_simulate_knockout():
    return jsonify({"error": "Simulation is disabled as the World Cup has started."}), 403

@app.route("/api/match/sync-all", methods=["POST"])
@admin_required
def api_match_sync_all():
    """Admin: scan official API for all finished matches and record any that are missing."""
    data = load_data()
    headers = {"X-Auth-Token": FOOTBALL_API_KEY} if FOOTBALL_API_KEY else {}
    try:
        resp = requests.get(
            f"{FOOTBALL_API_BASE}/competitions/{WC2026_COMPETITION}/matches",
            headers=headers, params={"status": "FINISHED"}, timeout=15
        )
        if resp.status_code != 200:
            return jsonify({"error": f"API error: {resp.status_code}"}), 500
        
        matches = resp.json().get("matches", [])
        if not matches:
            return jsonify({"ok": True, "count": 0, "message": "No finished matches found in API."})

        count_added = 0
        count_updated = 0
        
        # Track existing match IDs
        recorded_ids = {str(m.get("fixture_id")) for m in data.get("matches", []) if m.get("fixture_id")}
        
        for m in matches:
            api_id = str(m["id"])
            if api_id in recorded_ids:
                continue
                
            status = m.get("status", "")
            stage = _map_stage(m.get("stage", "group"))
            
            t1_raw = m["homeTeam"]["name"]
            t2_raw = m["awayTeam"]["name"]
            t1 = next((t["name"] for t in TEAMS if _is_name_match(t["name"], t1_raw)), t1_raw)
            t2 = next((t["name"] for t in TEAMS if _is_name_match(t["name"], t2_raw)), t2_raw)
            
            score = _get_api_match_score(m)
            s1 = score.get("home")
            s2 = score.get("away")
            
            extra = {}
            _fetch_detailed_bookings_and_extra(api_id, t1, t2, headers, extra)
            if not extra.get("hattrick_t1") and not extra.get("hattrick_t2"):
                _enrich_hattricks_from_fallback(t1, t2, extra)

            result = score_analyser(t1, t2, s1, s2, stage, extra, pts_config=data.get("points_config"))
            o1 = data["team_sold"].get(get_official_team_name(t1))
            o2 = data["team_sold"].get(get_official_team_name(t2))
            if o1: data["points"][o1] = data["points"].get(o1, 0) + result["team1"]["points"]
            if o2: data["points"][o2] = data["points"].get(o2, 0) + result["team2"]["points"]

            utc = m.get("utcDate", "")
            try:
                dt = datetime.strptime(utc, "%Y-%m-%dT%H:%M:%SZ")
                ts = dt.strftime("%d %b %Y, %H:%M")
            except:
                ts = datetime.now().strftime("%d %b %Y, %H:%M")

            match_record = {
                "id": str(uuid.uuid4())[:8], "team1": t1, "team2": t2, "score1": s1, "score2": s2,
                "stage": stage, "extra": extra, "owner1": o1, "owner2": o2, "result": result,
                "timestamp": ts, "flag1": get_team_flag(t1), "flag2": get_team_flag(t2),
                "fixture_id": api_id,
            }
            data["matches"].insert(0, match_record)
            count_added += 1
            
        if count_added > 0:
            save_data(data)
            
        return jsonify({"ok": True, "count": count_added, "message": f"Successfully synced {count_added} new matches."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/groups")
def groups_page():
    data = load_data()
    st = fetch_standings()
    groups = st["groups"] if st["groups"] else {
        letter: [{"position": i+1, "team": t, "played":0,"won":0,"draw":0,"lost":0,"gf":0,"ga":0,"gd":0,"pts":0} for i, t in enumerate(teams)]
        for letter, teams in WC2026_GROUPS.items()
    }
    return render_template("groups.html", data=data, groups=groups, teams=TEAMS, active_page="groups", get_player_color=get_player_color)


@app.route("/fixtures")
def fixtures():
    from collections import defaultdict, OrderedDict
    from datetime import timezone
    data = load_data()
    fx = fetch_all_fixtures()
    st = fetch_standings()
    team_rows = build_team_point_rows(data)
    knockout_sections = build_knockout_sections(data)
    by_round = defaultdict(list)
    for f in fx["fixtures"]: by_round[f["round"]].append(f)
    ordered_rounds = OrderedDict()
    for k in sorted(by_round.keys(), key=lambda r: (not str(r).isdigit(), r)): ordered_rounds[k] = by_round[k]
    all_owned = set()
    for teams_list in data.get("ownership", {}).values(): all_owned.update(teams_list)
    now_utc, next_matches = datetime.now(timezone.utc), {}
    for team in all_owned:
        for f in fx["fixtures"]:
            if f["status"] in ("SCHEDULED", "TIMED") and team in (f["home"], f["away"]):
                try: match_dt = datetime.strptime(f["utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                except ValueError: continue
                if match_dt > now_utc:
                    if team not in next_matches or match_dt < datetime.strptime(next_matches[team]["utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc):
                        next_matches[team] = f
                    break
    groups = st["groups"] if st["groups"] else {
        letter: [{"position": i+1, "team": t, "played":0,"won":0,"draw":0,"lost":0,"gf":0,"ga":0,"gd":0,"pts":0} for i, t in enumerate(teams)]
        for letter, teams in WC2026_GROUPS.items()
    }
    return render_template("fixtures.html", data=data, by_round=ordered_rounds, groups=groups, all_owned=all_owned, next_matches=next_matches, team_rows=team_rows, knockout_sections=knockout_sections, fx_error=fx["error"], st_error=st["error"], teams=TEAMS, active_page="fixtures", get_player_color=get_player_color)

def get_predicted_standings(data):
    # Start with current actual points
    simulated_points = {p["name"]: data.get("points", {}).get(p["name"], 0) for p in data.get("players", [])}
    
    sorted_groups = calculate_local_group_standings(data)
    
    thirds = []
    for l in "ABCDEFGHIJKL":
        if l in sorted_groups and len(sorted_groups[l]) >= 3:
            thirds.append(sorted_groups[l][2])
            
    sorted_thirds = sorted(thirds, key=lambda x: (-x["pts"], -x["gd"], -x["gf"], x["team"]))
    q_3rds = [(t["team"], get_team_group(t["team"])) for t in sorted_thirds[:8]]
    
    slots_3rd = [
        (74, "E"), (77, "I"), (79, "A"), (80, "L"),
        (81, "D"), (82, "G"), (85, "B"), (87, "K")
    ]
    assigned_3rds = assign_3rds(slots_3rd, q_3rds)
    if not assigned_3rds:
        assigned_3rds = {match_num: q_3rds[i][0] for i, (match_num, _) in enumerate(slots_3rd) if i < len(q_3rds)}
        
    resolved_cache = {}
    
    predictions = []
    
    # We resolve all knockout matches from 73 to 104
    for match_num in range(73, 105):
        outcome = resolve_match_outcome(match_num, data, sorted_groups, assigned_3rds, resolved_cache)
        if not outcome.get("played"):
            team1, team2 = outcome["team1"], outcome["team2"]
            winner = outcome["winner"]
            if team1 != "TBD" and team2 != "TBD" and winner != "TBD":
                if match_num <= 88: stage = "r32"
                elif match_num <= 96: stage = "r16"
                elif match_num <= 100: stage = "qf"
                elif match_num <= 102: stage = "sf"
                elif match_num == 103: stage = "3rd"
                else: stage = "final"
                
                if stage == "3rd":
                    continue
                    
                s1 = 2 if winner == team1 else 1
                s2 = 1 if winner == team1 else 2
                
                result = score_analyser(team1, team2, s1, s2, stage, extra={}, pts_config=data.get("points_config"))
                o1 = data.get("team_sold", {}).get(get_official_team_name(team1))
                o2 = data.get("team_sold", {}).get(get_official_team_name(team2))
                
                predictions.append({
                    "match_num": match_num,
                    "stage": stage.upper(),
                    "team1": team1,
                    "team2": team2,
                    "predicted_winner": winner,
                    "owner1": o1 or "Unowned",
                    "owner2": o2 or "Unowned",
                    "pts1": result["team1"]["points"],
                    "pts2": result["team2"]["points"],
                })
                
                if o1:
                    simulated_points[o1] += result["team1"]["points"]
                if o2:
                    simulated_points[o2] += result["team2"]["points"]
                    
    # Format rows
    pred_rows = []
    for name, final_pts in simulated_points.items():
        curr_pts = data.get("points", {}).get(name, 0)
        proj_earned = final_pts - curr_pts
        pred_rows.append({
            "name": name,
            "current_points": curr_pts,
            "projected_earned": proj_earned,
            "projected_final": final_pts,
        })
    pred_rows.sort(key=lambda x: (-x["projected_final"], x["name"]))
    return pred_rows, predictions

@app.route("/standings")
def standings():
    data = load_data()
    rows = []
    team_rows = build_team_point_rows(data)
    for p in team_rows:
        name = p["name"]
        recent = [m for m in data["matches"] if m.get("owner1") == name or m.get("owner2") == name][:5]
        rows.append({
            "name": name, 
            "pts": p["pts"], 
            "owned": p["owned"], 
            "matches_played": p["matches_played"], 
            "recent": recent, 
            "teams": p["teams"], 
            "team_points": p["team_points"],
            "active_teams_count": p["active_teams_count"],
            "eliminated_teams_count": p["eliminated_teams_count"]
        })
    pred_rows, future_preds = get_predicted_standings(data)
    return render_template(
        "standings.html", 
        data=data, 
        rows=rows, 
        team_rows=team_rows, 
        teams=TEAMS, 
        active_page="standings", 
        get_player_color=get_player_color,
        pred_rows=pred_rows,
        future_preds=future_preds
    )

@app.route("/team-leaderboard")
def team_leaderboard():
    data, matches, team_stats = load_data(), load_data().get("matches", []), {}
    for t in TEAMS: team_stats[t["name"]] = {"name": t["name"], "flag": t["flag"], "points": 0, "played": 0, "won": 0, "drawn": 0, "lost": 0, "owner": data.get("team_sold", {}).get(t["name"], "Unowned")}
    for m in matches:
        t1, t2, s1, s2, res = m["team1"], m["team2"], m["score1"], m["score2"], m.get("result", {})
        if t1 in team_stats:
            team_stats[t1]["points"] += res.get("team1", {}).get("points", 0)
            team_stats[t1]["played"] += 1
            if s1 > s2: team_stats[t1]["won"] += 1
            elif s1 == s2: team_stats[t1]["drawn"] += 1
            else: team_stats[t1]["lost"] += 1
        if t2 in team_stats:
            team_stats[t2]["points"] += res.get("team2", {}).get("points", 0)
            team_stats[t2]["played"] += 1
            if s2 > s1: team_stats[t2]["won"] += 1
            elif s1 == s2: team_stats[t2]["drawn"] += 1
            else: team_stats[t2]["lost"] += 1
    return render_template("team_leaderboard.html", data=data, teams=sorted(team_stats.values(), key=lambda x: x["points"], reverse=True), active_page="team-leaderboard", get_player_color=get_player_color)

@app.route("/match/<match_id>")
def match_detail(match_id):
    data = load_data()
    match = next((m for m in data["matches"] if m["id"] == match_id), None)
    if not match: return "Match not found", 404
    if match.get("score1") is None or match.get("score2") is None:
        return redirect(url_for("fixtures"))
    return render_template("match_detail.html", match=match, data=data, active_page=None, no_points=bool(match.get("extra", {}).get("third_place") or match.get("round_label") == "3rd Place Play-off"))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
