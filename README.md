# ✈️ Flight deal finder (Madrid ⇄ Paris and meetups)

Checks prices 4 times a day on GitHub Actions (free, no server) and messages you on Telegram when it finds:

- 🗼 **Visit to Paris**: MAD → CDG/ORY, return ≤ €150 per person
- 🏠 **Visit to Spain**: CDG/ORY → Madrid, Valencia, Zaragoza or Barcelona (you take the train 🚄 to the last three), return ≤ €150 per person
- 💑 **Meetup**: Madrid → X **and** Paris → X on the same weekend, with both tickets adding up to ≤ €200

Always **direct flights**, **Friday or Saturday → Sunday or Monday**, and **never Beauvais (BVA) or Vatry (XCR)**, neither outbound nor return, on any route.
All of this can be changed in [`config.yaml`](config.yaml).

## How it works

```
GitHub Actions (4 times a day)
 │
 ├─ 1. RADAR · Travelpayouts ──── covers every route × 4 months (cached prices, free)
 ├─ 2. SCAN · Google Flights ──── Madrid ⇄ CDG/ORY, every weekend for the next 8 weeks
 ├─ 3. CHECK ──────────────────── anything that looks cheap is re-checked live
 │      Google Flights  ──if Google blocks us──▶  SerpApi (plan B, 200 searches/month)
 ├─ 4. DECIDE ─────────────────── below the limit? far below the usual price? (🔥)
 ├─ 5. ANTI-SPAM ──────────────── no repeated alerts unless the price drops another 10 %
 ├─ 6. TELEGRAM ───────────────── one message with all new deals and links
 └─ 7. MEMORY ─────────────────── saves history and alerts in data/state.json (automatic commit)
```

| Source | Role | Cost | Weak spot |
|---|---|---|---|
| **Travelpayouts** | Radar: sees whole months at once | Free | Prices from hours or days ago |
| **Google Flights** (`fast-flights`) | Live price and scan of the main route | Free | It is scraping: Google may block it |
| **SerpApi** | Plan B when Google fails | Free up to ~250/month | Few searches |

For meetups, if the radar only has a price for one of the two sides, the system estimates the other with the cheapest it has seen and, if the sum looks promising, searches both sides live.

## Setup (about 20 minutes)

### 1. Telegram bot
1. In Telegram, open **@BotFather** → `/newbot` → give it a name → copy the **token**.
2. Create a group with your partner, add the bot (search for its exact `@username`) and send `/start@your_bot_username` in the group.
3. Put the token in a `.env` file (see below) and get the chat id:
   ```bash
   python -m vuelos.telegram_setup
   ```

### 2. Travelpayouts (radar)
Sign up for free at <https://www.travelpayouts.com> → **Tools → API** → copy the **API token**.

### 3. SerpApi (plan B)
Sign up for free at <https://serpapi.com> → **Dashboard → API key**.

### 4. GitHub
1. Push this folder to your repository (it can be **private**).
2. **Settings → Secrets and variables → Actions → New repository secret** and create:
   `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TRAVELPAYOUTS_TOKEN`, `SERPAPI_KEY`
3. **Actions** → "Find flight deals" → **Run workflow** to try it right away.

From then on it runs by itself. If the radar or SerpApi have no key, the system works with whatever it has.

## Running it on your computer

```bash
pip install -r requirements.txt
```
Create a `.env` file (it is never uploaded to GitHub) with:
```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
TRAVELPAYOUTS_TOKEN=...
SERPAPI_KEY=...
```
```bash
python -m vuelos --test-telegram
```
```bash
python -m vuelos --dry-run
```
`--dry-run` really searches, but prints the messages instead of sending them.

## Common tweaks (`config.yaml`)
- **A weekend one of you can't make it**: add a line to `blocked_dates`, e.g. `- { from: 2026-12-04, to: 2026-12-06, who: Clau }`. Any trip touching those dates is skipped.
- **Names in the messages**: `people.madrid` and `people.paris` (Telegram messages are in French).
- **Another destination**: add a line to `meetup.destinations` (`city` = the city's IATA code).
- **Custom limit for one meetup**: `max_total: 180` on that line.
- **Other weekends** (e.g. Thursday → Sunday): add `[3, 6]` to `weekend_patterns`.
- **Another city you can reach by train**: add it to `visit.from_paris_to` (and its name to `CITIES` in `vuelos/models.py`).
- **More or fewer runs**: change the `cron` in `.github/workflows/vuelos.yml`.

## Notes
- Prices are per person, return, in euros, without checked luggage.
- ✅ = checked live; ⚠️ = cached price (may have changed).
- 🔥 shows up once there are at least 5 runs of history and the price is 25 % below the usual price on that route.
- A private repository gets 2,000 free Actions minutes a month; this uses about 1,000–1,200 (public repositories are unlimited).
- If Google changes its website, `fast-flights` may stop working until it gets updated. Meanwhile SerpApi keeps covering the checks, and if nothing can be fetched you get a Telegram warning (at most once a day).

For a full explanation of how and why it was built this way, see [GUIDE.md](GUIDE.md).
