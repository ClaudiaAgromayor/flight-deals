"""SerpApi (Google Flights through a paid API): plan B when Google blocks us."""
from datetime import date

import requests

from ..models import Offer, ProviderError

API = "https://serpapi.com/search.json"


class SerpApi:
    def __init__(self, cfg, api_key, banned, state):
        self.key = api_key
        self.limit = cfg.get("monthly_limit", 200)
        self.banned = set(banned)
        # This month's search counter, stored in state.json so we stay within the free plan
        month = date.today().strftime("%Y-%m")
        self.usage = state.setdefault("serpapi", {})
        if self.usage.get("month") != month:
            self.usage.clear()
            self.usage.update(month=month, used=0)

    @property
    def available(self):
        return bool(self.key) and self.usage["used"] < self.limit

    def search(self, origin, dest, depart, ret):
        if not self.available:
            raise ProviderError("SerpApi has no key or no free searches left this month")
        params = {
            "engine": "google_flights", "departure_id": origin, "arrival_id": dest,
            "outbound_date": depart.isoformat(), "return_date": ret.isoformat(),
            "type": "1", "stops": "1", "currency": "EUR", "hl": "en", "gl": "es",
            "api_key": self.key,
        }
        self.usage["used"] += 1
        try:
            data = requests.get(API, params=params, timeout=60).json()
        except Exception as e:
            raise ProviderError(f"SerpApi not responding ({e})") from e
        if "error" in data:
            if "returned any results" in data["error"]:
                return []
            raise ProviderError(f"SerpApi: {data['error']}")

        link = data.get("search_metadata", {}).get("google_flights_url", "")
        offers = []
        for item in data.get("best_flights", []) + data.get("other_flights", []):
            segs = item.get("flights") or []
            if len(segs) != 1 or not item.get("price"):
                continue
            seg = segs[0]
            o, d = seg["departure_airport"]["id"], seg["arrival_airport"]["id"]
            if (o, d) != (origin, dest) or {o, d} & self.banned:
                continue
            offers.append(Offer(origin, dest, depart, ret, float(item["price"]), [seg.get("airline", "")],
                                "serpapi", link, True, seg["departure_airport"].get("time", "")[-5:] or None))
        return offers
