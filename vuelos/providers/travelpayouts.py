"""Travelpayouts / Aviasales Data API: the "radar". Free and covers whole months at once,
but these are prices other users saw recently (cache), not live prices."""
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
        """Direct return flights departing in `month` (YYYY-MM). origin/dest may be a city code (PAR)."""
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
            raise ProviderError(f"Travelpayouts not responding ({e})") from e
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
