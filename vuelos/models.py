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
    """La fuente no responde o nos ha bloqueado (distinto de "no hay vuelos")."""


@dataclass
class Offer:
    """Un vuelo directo de ida y vuelta, precio por persona en EUR."""

    origin: str
    dest: str
    depart: date
    ret: date
    price: float
    airlines: list[str]
    source: str          # google | serpapi | travelpayouts
    link: str
    verified: bool       # True = precio en tiempo real; False = precio en caché
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
    hist_key: str        # con qué historial se compara para decidir si es 🔥
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
        # Mismo viaje = mismo tipo, destino y fechas (aunque cambie el aeropuerto)
        return f"{self.kind}|{self.title}|{self.depart}|{self.ret}"
