from __future__ import annotations

from dataclasses import dataclass
from datetime import date

AIRLINES = {
    "IB": "Iberia", "I2": "Iberia Express", "UX": "Air Europa", "VY": "Vueling",
    "TO": "Transavia", "HV": "Transavia", "AF": "Air France", "KL": "KLM",
    "FR": "Ryanair", "U2": "easyJet", "EC": "easyJet", "DS": "easyJet",
    "TP": "TAP", "AZ": "ITA Airways", "V7": "Volotea", "SN": "Brussels Airlines",
    "W6": "Wizz Air", "LH": "Lufthansa", "LX": "Swiss",
}


CITIES = {"MAD": "Madrid", "VLC": "Valencia", "ZAZ": "Zaragoza", "BCN": "Barcelona"}


class ProviderError(Exception):
    """The source is down or has blocked us (not the same as "no flights")."""


@dataclass
class Offer:
    """A direct return flight, price per person in EUR."""

    origin: str
    dest: str
    depart: date
    ret: date
    price: float
    airlines: list[str]
    source: str          # google | serpapi | travelpayouts
    link: str
    verified: bool       # True = live price; False = cached price
    depart_time: str | None = None

    @property
    def route_key(self) -> tuple[str, str, date, date]:
        return (self.origin, self.dest, self.depart, self.ret)

    @property
    def airline_names(self) -> str:
        return ", ".join(AIRLINES.get(a, a) for a in self.airlines if a) or "?"


@dataclass
class Deal:
    kind: str            # visit_paris | visit_spain | meetup
    title: str
    legs: list[Offer]
    limit: float
    hist_key: str        # which history it is compared with to decide if it is 🔥
    hot: bool = False

    @property
    def total(self) -> float:
        return sum(leg.price for leg in self.legs)

    @property
    def depart(self) -> date:
        return self.legs[0].depart

    @property
    def ret(self) -> date:
        return self.legs[0].ret

    @property
    def key(self) -> str:
        # Same trip = same kind, destination and dates (even if the airport changes)
        return f"{self.kind}|{self.title}|{self.depart}|{self.ret}"
