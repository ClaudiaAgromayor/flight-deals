"""Telegram messages (written in French for the "On se voit quand?" group)."""
from html import escape

import requests

from .dates import fmt

API = "https://api.telegram.org/bot{token}/{method}"
MAX_LEN = 3800  # Telegram cuts messages at 4096

# Display names only: config/history keep the English names so past alerts still match
FRENCH = {
    "Lisbon": "Lisbonne", "Venice": "Venise", "Bologna": "Bologne", "Brussels": "Bruxelles",
    "Valencia": "Valence", "Zaragoza": "Saragosse", "Barcelona": "Barcelone", "London": "Londres",
}


def send(token, chat_id, text):
    r = requests.post(API.format(token=token, method="sendMessage"), timeout=30, json={
        "chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True,
    })
    if not r.ok:
        raise RuntimeError(f"Telegram rejected the message: {r.text}")


def _city(deal):
    name = deal.hist_key.split("|", 1)[1]
    return FRENCH.get(name, name)


def _a(city):
    return f"à {city}"


def _leg(o, who=None):
    hour = f" {o.depart_time}" if o.depart_time else ""
    check = "✅" if o.verified else "⚠️ en cache"
    link = f' · <a href="{escape(o.link)}">voir</a>' if o.link else ""
    prefix = f"{who} : " if who else ""
    return f"{prefix}{o.origin}→{o.dest}{hour} · {o.price:.0f} € · {escape(o.airline_names)} {check}{link}"


def format_deal(d, people):
    clau, titou = escape(people["madrid"]), escape(people["paris"])
    fire = "🔥 " if d.hot else ""
    when = f"{fmt(d.depart)} → {fmt(d.ret)}"
    city = escape(_city(d))

    if d.kind == "meetup":
        a, b = d.legs
        return (f"{fire}💑 <b>Rendez-vous {_a(city)}</b> · <b>{d.total:.0f} €</b> à deux\n{when}\n"
                f"• {_leg(a, f'{clau} vole depuis Madrid')}\n"
                f"• {_leg(b, f'{titou} vole depuis Paris')}")
    if d.kind == "meetup_train":
        return (f"{fire}💑 <b>Rendez-vous {_a(city)}</b> · <b>{d.total:.0f} €</b> A/R\n{when}\n"
                f"{clau} vole depuis Madrid : {_leg(d.legs[0])}\n"
                f"{titou} prend le train depuis Paris")
    if d.kind == "visit_paris":
        return (f"{fire}🗼 <b>{clau} va à Paris</b> · <b>{d.total:.0f} €</b> A/R\n{when}\n"
                f"{_leg(d.legs[0])}")
    # visit_spain
    leg = d.legs[0]
    if leg.dest == "MAD":
        return (f"{fire}🏠 <b>{titou} vient à Madrid</b> · <b>{d.total:.0f} €</b> A/R\n{when}\n"
                f"{titou} prend l'avion depuis Paris : {_leg(leg)}")
    return (f"{fire}🚄 <b>{titou} vole {_a(city)}</b> · <b>{d.total:.0f} €</b> A/R\n{when}\n"
            f"{titou} prend l'avion depuis Paris : {_leg(leg)}\n"
            f"{clau} prend le train depuis Madrid")


def build_messages(deals, people):
    header = f"✈️ <b>{len(deals)} bon{'s' if len(deals) != 1 else ''} plan{'s' if len(deals) != 1 else ''} vols</b>\n"
    footer = "\n<i>Prix par personne, aller-retour, vols directs. ⚠️ = prix en cache, à vérifier.</i>"
    messages, cur = [], header
    for block in (format_deal(d, people) for d in deals):
        if len(cur) + len(block) + len(footer) > MAX_LEN:
            messages.append(cur)
            cur = ""
        cur += "\n" + block + "\n"
    messages.append(cur + footer)
    return messages
