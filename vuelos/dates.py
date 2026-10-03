from datetime import date, timedelta

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


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


def fmt(d: date) -> str:
    return f"{DAYS[d.weekday()]} {d.day} {MONTHS[d.month - 1]}"
