import json
from datetime import date
from statistics import median

from .config import ROOT

STATE_FILE = ROOT / "data" / "state.json"
HISTORY_LEN = 120


def load_state():
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(state):
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def record_history(state, key, prices):
    """Store this run's median price so we know what "usual" looks like."""
    if not prices:
        return
    hist = state.setdefault("history", {}).setdefault(key, [])
    hist.append([date.today().isoformat(), round(median(prices), 2)])
    del hist[:-HISTORY_LEN]


def usual_price(state, key, min_samples=5):
    hist = state.get("history", {}).get(key, [])
    if len(hist) < min_samples:
        return None
    return median(v for _, v in hist)


def select_new(deals, state, realert_drop):
    """Drop what we already alerted about, unless it has dropped noticeably further."""
    alerted = state.setdefault("alerted", {})
    today = date.today().isoformat()
    for k in [k for k, v in alerted.items() if v["depart"] < today]:
        del alerted[k]
    return [
        d for d in deals
        if d.key not in alerted or d.total <= alerted[d.key]["price"] * (1 - realert_drop)
    ]


def mark_alerted(deals, state):
    alerted = state.setdefault("alerted", {})
    for d in deals:
        alerted[d.key] = {"price": d.total, "depart": d.depart.isoformat()}
