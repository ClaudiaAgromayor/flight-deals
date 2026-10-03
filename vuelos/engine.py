"""The brain: gathers prices from the three sources, double-checks candidates and decides what is a deal.

One run, step by step:
  1. Radar (Travelpayouts): cached prices for every route and month.
  2. Scan (Google Flights): the priority route Madrid <-> Paris, weekend by weekend.
  3. Candidates: anything that looks below the limit is re-checked live
     (Google Flights; if Google fails, SerpApi).
  4. Deals: visits <= limit, and meetups where the two tickets add up to <= limit.
"""
from datetime import date, timedelta

from .dates import is_blocked, weekend_pairs
from .models import CITIES, Deal, ProviderError
from .providers import GoogleFlights, SerpApi, Travelpayouts
from .state import record_history, usual_price


def _price(offer):
    return offer.price


class Engine:
    def __init__(self, cfg, state, use_google=True, log=print):
        self.cfg, self.state, self.log = cfg, state, log
        banned, prov, sec = cfg["banned_airports"], cfg["providers"], cfg["secrets"]

        self.tp = (Travelpayouts(sec["TRAVELPAYOUTS_TOKEN"], banned)
                   if prov["travelpayouts"]["enabled"] and sec["TRAVELPAYOUTS_TOKEN"] else None)
        self.google = GoogleFlights(prov["google"], banned) if prov["google"]["enabled"] and use_google else None
        self.serp = SerpApi(prov["serpapi"], sec["SERPAPI_KEY"], banned, state) if prov["serpapi"]["enabled"] else None
        self.google_ok = self.google is not None
        self.budget = prov["google"].get("max_verifications", 40)
        self.tolerance = 1 + prov["travelpayouts"].get("tolerance", 0.15)

        self.pairs = [p for p in weekend_pairs(cfg["weekend_patterns"], cfg["weeks_ahead"])
                      if not is_blocked(*p, cfg.get("blocked_dates"))]
        self.pair_set = set(self.pairs)
        self.paris = set(cfg["paris_airports"])
        self.offers = {}      # (origin, dest, depart, return) -> most reliable / cheapest offer
        self.checked = set()  # keys already searched live during this run
        self.errors = []

    # ── collecting prices ───────────────────────────────────────

    def add(self, offers):
        for o in offers:
            if (o.depart, o.ret) not in self.pair_set:
                continue
            cur = self.offers.get(o.route_key)
            if (cur is None or (o.verified and not cur.verified)
                    or (o.verified == cur.verified and o.price < cur.price)):
                self.offers[o.route_key] = o

    def _fail(self, msg):
        self.errors.append(msg)
        self.log(f"⚠️  {msg}")

    def discover(self):
        """Step 1: Travelpayouts radar over every route and month."""
        if not self.tp:
            self.log("· Travelpayouts disabled (TRAVELPAYOUTS_TOKEN missing)")
            return
        routes = {(es, "PAR") for es in self.cfg["visit"]["to_paris_from"]}
        routes |= {("PAR", es) for es in self.cfg["visit"]["from_paris_to"]}
        for dest in self.cfg["meetup"]["destinations"]:
            routes |= {(es, dest["city"]) for es in self.cfg["meetup"]["spain_airports"]}
            if not dest.get("paris_by_train"):
                routes.add(("PAR", dest["city"]))
        months = sorted({d.strftime("%Y-%m") for d, _ in self.pairs})
        for o, d in sorted(routes):
            for m in months:
                try:
                    self.add(self.tp.month_offers(o, d, m))
                except ProviderError as e:
                    self._fail(str(e))
                    if self.tp.calls > 3 and len(self.errors) >= 3:
                        return  # bad token or API down: stop insisting
        self.log(f"· Travelpayouts: {self.tp.calls} requests, {len(self.offers)} cached prices")

    def scan_google(self):
        """Step 2: Google Flights checks the priority route weekend by weekend."""
        if not self.google_ok:
            return
        v = self.cfg["visit"]
        until = date.today() + timedelta(weeks=v["google_weeks_ahead"])
        for dep, ret in self.pairs:
            if dep > until:
                break
            for es in v["google_scan_airports"]:
                for fr in self.cfg["paris_airports"]:
                    routes = []
                    if es in v["to_paris_from"]:
                        routes.append((es, fr))
                    if es in v["from_paris_to"]:
                        routes.append((fr, es))
                    for o, d in routes:
                        self.checked.add((o, d, dep, ret))
                        try:
                            self.add(self.google.search(o, d, dep, ret))
                        except ProviderError as e:
                            self.google_ok = False
                            self._fail(str(e))
                            return
        self.log(f"· Google Flights: {self.google.calls} scan searches")

    def live_search(self, o, d, dep, ret):
        """Real-time price. None = could not be checked."""
        if self.google_ok:
            try:
                return self.google.search(o, d, dep, ret)
            except ProviderError as e:
                self.google_ok = False
                self._fail(f"{e} → falling back to SerpApi")
        if self.serp and self.serp.available:
            try:
                return self.serp.search(o, d, dep, ret)
            except ProviderError as e:
                self._fail(str(e))
        return None

    def verify(self, o, d, dep, ret):
        """Step 3: double-check a candidate. Returns the best offer (verified if possible) or None."""
        key = (o, d, dep, ret)
        if key not in self.checked and self.budget > 0:
            self.checked.add(key)
            self.budget -= 1
            live = self.live_search(o, d, dep, ret)
            if live is not None:
                self.offers.pop(key, None)  # the live price beats the cached one
                self.add(live)
        return self.offers.get(key)

    # ── deciding deals ──────────────────────────────────────────

    def visit_deals(self):
        v = self.cfg["visit"]
        to_paris, from_paris, maxp = set(v["to_paris_from"]), set(v["from_paris_to"]), v["max_price"]
        # Groups: you to Paris (CDG or ORY, either is fine) and him to each Spanish city separately
        groups = {}
        for o in self.offers.values():
            if o.origin in to_paris and o.dest in self.paris:
                groups.setdefault(("visit_paris", "Paris"), []).append(o)
            elif o.origin in self.paris and o.dest in from_paris:
                groups.setdefault(("visit_spain", CITIES.get(o.dest, o.dest)), []).append(o)

        deals = []
        for (kind, city), offers in groups.items():
            hist_key = f"{kind}|{city}"
            record_history(self.state, hist_key, [o.price for o in offers])
            best = {}  # (depart, return) -> cheapest offer for that weekend
            for c in sorted(offers, key=_price):
                if c.price > maxp * self.tolerance:
                    break
                c = c if c.verified else self.verify(*c.route_key)
                when = (c.depart, c.ret) if c else None
                if c and c.price <= maxp and (when not in best or c.price < best[when].price):
                    best[when] = c
            deals += [Deal(kind, f"Visit to {city}", [o], maxp, hist_key) for o in best.values()]
        return deals

    def _cheapest(self, origins, airports, dep=None, ret=None):
        opts = [o for o in self.offers.values()
                if o.origin in origins and o.dest in airports
                and (dep is None or (o.depart, o.ret) == (dep, ret))]
        return min(opts, key=_price, default=None)

    def _verify_side(self, origins, airports, dep, ret, current):
        if current and current.verified:
            return current
        if current:
            return self.verify(*current.route_key)
        for o in origins:              # no price for this side yet: go and look for one
            for d in airports:
                found = self.verify(o, d, dep, ret)
                if found:
                    return found
        return None

    def meetup_deals(self):
        m = self.cfg["meetup"]
        es = set(m["spain_airports"])
        deals = []
        for dest in m["destinations"]:
            airports = set(dest["airports"])
            if dest.get("paris_by_train"):
                deals += self._train_meetup_deals(dest, es, airports)
                continue
            # Optional limit per ticket; if both are set they replace the default total limit
            max_a = dest.get("max_madrid", float("inf"))
            max_b = dest.get("max_paris", float("inf"))
            per_side = "max_madrid" in dest and "max_paris" in dest
            limit = dest.get("max_total", max_a + max_b if per_side else m["default_max_total"])
            floor_es = self._cheapest(es, airports)
            floor_fr = self._cheapest(self.paris, airports)
            if not floor_es and not floor_fr:
                continue
            sums, candidates = [], []
            for dep, ret in self.pairs:
                a = self._cheapest(es, airports, dep, ret)
                b = self._cheapest(self.paris, airports, dep, ret)
                if a and b:
                    sums.append(a.price + b.price)
                # If one side has no price, estimate it with the cheapest seen for that side
                est_a = a.price if a else (floor_es.price if floor_es else None)
                est_b = b.price if b else (floor_fr.price if floor_fr else None)
                if (est_a is not None and est_b is not None and est_a + est_b <= limit * self.tolerance
                        and est_a <= max_a * self.tolerance and est_b <= max_b * self.tolerance):
                    candidates.append((est_a + est_b, dep, ret, a, b))
            hist_key = f"meetup|{dest['name']}"
            record_history(self.state, hist_key, sums)

            for _, dep, ret, a, b in sorted(candidates, key=lambda c: c[0]):
                a = self._verify_side(es, airports, dep, ret, a)
                b = self._verify_side(self.paris, airports, dep, ret, b) if a else None
                if a and b and a.price + b.price <= limit and a.price <= max_a and b.price <= max_b:
                    deals.append(Deal("meetup", f"Meetup in {dest['name']}", [a, b], limit, hist_key))
        return deals

    def _train_meetup_deals(self, dest, es, airports):
        """Meetup where only the Madrid side flies (Paris side takes the train): one ticket, its own limit."""
        limit = dest["max_price"]
        hist_key = f"meetup_train|{dest['name']}"
        record_history(self.state, hist_key,
                       [o.price for o in self.offers.values() if o.origin in es and o.dest in airports])
        deals = []
        for dep, ret in self.pairs:
            a = self._cheapest(es, airports, dep, ret)
            if not a or a.price > limit * self.tolerance:
                continue
            a = self._verify_side(es, airports, dep, ret, a)
            if a and a.price <= limit:
                deals.append(Deal("meetup_train", f"Meetup in {dest['name']}", [a], limit, hist_key))
        return deals

    def run(self):
        self.discover()
        self.scan_google()
        deals = self.visit_deals() + self.meetup_deals()
        hot = self.cfg["alerts"]["hot_vs_median"]
        for d in deals:
            usual = usual_price(self.state, d.hist_key)
            d.hot = usual is not None and d.total <= usual * hot
        self.log(f"· {len(self.offers)} prices in total, {len(deals)} deals, "
                 f"{len(self.checked)} live checks")
        return sorted(deals, key=lambda d: (not d.hot, d.total / d.limit))
