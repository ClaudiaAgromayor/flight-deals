from datetime import date, timedelta

# Telegram messages are in French
DAYS = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]
MONTHS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def weekend_pairs(patterns, weeks_ahead, today=None):
    """Every (depart, return) pair matching the patterns, e.g. Fri->Mon."""
    today = today or date.today()
    end = today + timedelta(weeks=weeks_ahead)
    pairs = []
    d = today + timedelta(days=1)
    while d <= end:
        for dep_wd, ret_wd in patterns:
            if d.weekday() == dep_wd:
                gap = (ret_wd - dep_wd) % 7 or 7
                pairs.append((d, d + timedelta(days=gap)))
        d += timedelta(days=1)
    return sorted(pairs)


def _as_date(value):
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def is_blocked(depart, ret, blocked):
    """True if the trip overlaps any blocked range (e.g. Fri 16 -> Mon 19 overlaps 16-18)."""
    return any(_as_date(b["from"]) <= ret and depart <= _as_date(b["to"]) for b in blocked or [])


def fmt(d: date) -> str:
    return f"{DAYS[d.weekday()]} {d.day} {MONTHS[d.month - 1]}"
