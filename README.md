# Flight deal finder

A small program that watches flight prices between Madrid and Paris and sends a Telegram message when it finds a good deal. It runs by itself four times a day on GitHub Actions, so no computer needs to be on.

## What it looks for

Clau lives in Madrid and Titou lives in Paris. Three kinds of trips are checked:

- **Clau visits Paris:** return flight Madrid → Paris, €150 or less.
- **Titou visits Spain:** return flight Paris → Madrid, €150 or less. Also Paris → Valencia and Zaragoza, where Clau can arrive by train.
- **We meet somewhere else:** both fly to the same city on the same weekend, €200 or less for the two tickets together (Lisbon, Porto, Rome, Milan, Nice, Bilbao...). Marseille: €120 or less per ticket. Amsterdam: Titou goes by train, so only the Madrid flight is checked, up to €220.

Prices are per person, return, without checked luggage.

## Rules it always follows

- **Direct flights only.**
- **Weekends only:** out on Friday or Saturday, back on Sunday or Monday.
- **No Beauvais or Vatry.** In Paris only CDG and Orly are accepted.
- **Blocked weekends are skipped** (listed in `blocked_dates`).

## How it works, in short

Each run gets prices from Travelpayouts (wide view), Google Flights (real prices for the main route) and SerpApi (backup if Google blocks it). It keeps only trips under the price limit, marks the ones much cheaper than usual, skips deals already sent, and posts one Telegram message (in French) with links. History is saved in `data/state.json`. If no prices can be fetched, it sends a warning instead of failing silently.

In the messages, ✅ means confirmed live on Google Flights, ⚠️ means a cached price that is worth double-checking, and 🔥 means much lower than usual.

## Configuration

Everything lives in [`config.yaml`](config.yaml), no code changes needed: price limits, meetup cities, blocked weekends, weekend days and names. Push the change and the next run uses it.

## Quick start

```bash
pip install -r requirements.txt
python -m vuelos --dry-run        # real search, prints messages instead of sending
python -m vuelos --test-telegram  # sends a test message
```

Required secrets (in `.env` locally and in GitHub Actions secrets): `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TRAVELPAYOUTS_TOKEN`, `SERPAPI_KEY`.

> Always `git pull` before changing anything: the program commits its history to the repository after every run.

## More documentation

- [docs/SETUP.md](docs/SETUP.md): full setup from scratch, how each run works, config examples, commands and known issues.
- [GUIDE.md](GUIDE.md): how this was built and why each decision was made.
