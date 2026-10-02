"""Google Flights vía fast-flights: precio real y gratis, pero es scraping."""
import time

from fast_flights import FlightQuery, Passengers, create_query
from fast_flights.exceptions import FlightsNotFound
from fast_flights.parser import parse
from primp import Client

from ..models import Offer, ProviderError

URL = "https://www.google.com/travel/flights"
# Desde IPs europeas Google enseña antes la pantalla de cookies ("Antes de continuar");
# con esta cookie la damos por aceptada y llegamos directamente a los resultados.
CONSENT_COOKIE = "SOCS=CAESEwgDEgk0ODE3Nzk3MjQaAmVuIAEaBgiA_LyaBg; CONSENT=YES+"


class GoogleFlights:
    def __init__(self, cfg, banned):
        self.delay = cfg.get("delay_seconds", 2.5)
        self.banned = set(banned)
        self.client = Client(impersonate="chrome_145", impersonate_os="macos", referer=True, cookie_store=True)
        self._last = 0.0
        self.calls = 0

    def search(self, origin, dest, depart, ret):
        query = create_query(
            flights=[
                FlightQuery(date=depart.isoformat(), from_airport=origin, to_airport=dest),
                FlightQuery(date=ret.isoformat(), from_airport=dest, to_airport=origin),
            ],
            trip="round-trip",
            passengers=Passengers(adults=1),
            language="en-US",
            currency="EUR",
            max_stops=0,
        )
        wait = self.delay - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        try:
            html = self.client.get(URL, params=query.params(), headers={"Cookie": CONSENT_COOKIE}).text
        except Exception as e:
            raise ProviderError(f"Google Flights no responde ({e})") from e
        finally:
            self._last = time.monotonic()
            self.calls += 1

        try:
            results = parse(html)
        except FlightsNotFound:
            return []
        except Exception as e:
            # Página de bloqueo/captcha o Google ha cambiado su web
            raise ProviderError(f"Google Flights ha devuelto algo inesperado ({type(e).__name__})") from e

        offers = []
        for r in results:
            if not r.price or len(r.flights) != 1:   # solo directos
                continue
            seg = r.flights[0]
            o, d = seg.from_airport.code, seg.to_airport.code
            if (o, d) != (origin, dest) or {o, d} & self.banned:
                continue
            hh, mm = seg.departure.time
            offers.append(Offer(origin, dest, depart, ret, float(r.price), list(r.airlines),
                                "google", query.url(), True, f"{hh:02d}:{mm:02d}"))
        return offers
