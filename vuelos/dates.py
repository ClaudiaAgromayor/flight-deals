from datetime import date, timedelta

DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def weekend_pairs(patterns, weeks_ahead, today=None):
    """Todas las parejas (salida, vuelta) que encajan con los patrones, p. ej. vie->lun."""
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
    return f"{DIAS[d.weekday()]} {d.day} {MESES[d.month - 1]}"
