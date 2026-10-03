from html import escape

import requests

from .dates import fmt

API = "https://api.telegram.org/bot{token}/{method}"
MAX_LEN = 3800  # Telegram cuts messages at 4096


def send(token, chat_id, text):
    r = requests.post(API.format(token=token, method="sendMessage"), timeout=30, json={
        "chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True,
    })
    if not r.ok:
        raise RuntimeError(f"Telegram rejected the message: {r.text}")


def _leg(o, who=None):
    hour = f" {o.depart_time}" if o.depart_time else ""
    check = "✅" if o.verified else "⚠️ cached"
    link = f' · <a href="{escape(o.link)}">view</a>' if o.link else ""
    prefix = f"{who}: " if who else ""
    return f"{prefix}{o.origin}→{o.dest}{hour} · €{o.price:.0f} · {escape(o.airline_names)} {check}{link}"


def format_deal(d):
    fire = "🔥 " if d.hot else ""
    icon = {"visit_paris": "🗼", "visit_spain": "🏠", "meetup": "💑"}[d.kind]
    when = f"{fmt(d.depart)} → {fmt(d.ret)}"
    if d.kind == "meetup":
        a, b = d.legs
        return (f"{fire}{icon} <b>{escape(d.title)}</b> · <b>€{d.total:.0f}</b> for both\n"
                f"{when}\n• {_leg(a, 'Madrid')}\n• {_leg(b, 'Paris')}")
    train = "\n🚄 you take the train from Madrid" if d.kind == "visit_spain" and d.legs[0].dest != "MAD" else ""
    return f"{fire}{icon} <b>{escape(d.title)}</b> · <b>€{d.total:.0f}</b> return\n{when}\n{_leg(d.legs[0])}{train}"


def build_messages(deals):
    header = f"✈️ <b>{len(deals)} flight deal{'s' if len(deals) != 1 else ''}</b>\n"
    footer = "\n<i>Prices per person, return, direct flights. ⚠️ = cached price, double-check it.</i>"
    messages, cur = [], header
    for block in map(format_deal, deals):
        if len(cur) + len(block) + len(footer) > MAX_LEN:
            messages.append(cur)
            cur = ""
        cur += "\n" + block + "\n"
    messages.append(cur + footer)
    return messages
