"""Travelpayouts / Aviasales Data API: el "radar". Gratis y barre meses enteros,
pero son precios que otros usuarios han visto hace poco (caché), no en tiempo real."""
from datetime import date

import requests

from ..models import Offer, ProviderError

API = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"


class Travelpayouts:
    def __init__(self, token, banned):
        self.token = token
        self.banned = set(banned)
        self.calls = 0

    def month_offers(self, origin, dest, month):
        """Vuelos directos de ida y vuelta saliendo en `month` (YYYY-MM). origin/dest pueden ser ciudad (PAR)."""
        params = {
            "origin": origin, "destination": dest, "departure_at": month,
            "one_way": "false", "direct": "true", "currency": "eur",
            "sorting": "price", "unique": "false", "limit": 1000, "page": 1,
        }
        self.calls += 1
        try:
            r = requests.get(API, params=params, headers={"X-Access-Token": self.token}, timeout=30)
            data = r.json()
        except Exception as e:
            raise ProviderError(f"Travelpayouts no responde ({e})") from e
        if r.status_code != 200 or not data.get("success", False):
            raise ProviderError(f"Travelpayouts: {data.get('error') or r.status_code}")

        offers = []
        for it in data.get("data", []):
            if it.get("transfers") or it.get("return_transfers") or not it.get("return_at"):
                continue
            o = it.get("origin_airport") or it.get("origin")
            d = it.get("destination_airport") or it.get("destination")
            if {o, d} & self.banned:
                continue
            link = "https://www.aviasales.com" + it["link"] if it.get("link") else ""
            offers.append(Offer(
                o, d, date.fromisoformat(it["departure_at"][:10]), date.fromisoformat(it["return_at"][:10]),
                float(it["price"]), [it.get("airline", "")], "travelpayouts", link, False,
                it["departure_at"][11:16] or None,
            ))
        return offers
