# Flight deal finder

A small program that watches flight prices between Madrid and Paris, and sends a Telegram message when it finds a good deal.

I built it because flights between Madrid and Paris keep getting more expensive, and checking them by hand every day was exhausting. Now the program checks for us and only speaks up when something is actually worth it.

## What it looks for

There are two of us: Clau lives in Madrid and Titou lives in Paris. The program looks for three kinds of trips.

**Clau visits Paris.** A return flight from Madrid to Paris, for €150 or less.

**Titou visits Spain.** A return flight from Paris to Madrid, for €150 or less. It also checks flights from Paris to Valencia, Zaragoza and Barcelona, because Clau can easily take the train to meet him there.

**We meet somewhere else.** Both of us fly to the same city on the same weekend, and the two tickets together cost €200 or less. It checks places like Lisbon, Porto, Rome, Milan, Nice, Marseille and Bilbao. For Amsterdam it works a bit differently: Titou goes by train, so it only watches the flight from Madrid, up to €220.

All prices are per person, for a return trip, without checked luggage.

## The rules it always follows

- **Direct flights only.** No layovers.
- **Weekends only.** Leaving on Friday or Saturday, coming back on Sunday or Monday.
- **No Beauvais.** Some airlines advertise "Paris" but land in Beauvais (or Vatry), which is more than an hour away from the city. Those airports are never accepted, neither for leaving nor for arriving, on any route. In Paris it only uses Charles de Gaulle (CDG) and Orly (ORY).
- **Blocked weekends are skipped.** If one of us can't travel on a given weekend, it is added to a list and the program ignores any trip on those dates.

## How it works

The program runs by itself four times a day on GitHub, so no computer needs to be switched on. Each run goes through the same steps:

1. **It takes a wide look.** It asks Travelpayouts for prices on every route over the next four months. Travelpayouts is free and covers a lot of ground quickly, but its prices come from searches other people made recently, so they can be a little out of date.
2. **It checks the main route closely.** For Madrid and Paris, which matter most, it searches Google Flights directly, weekend by weekend, for the next eight weeks.
3. **It double-checks anything that looks cheap.** If a price from step 1 looks good, it searches it again on Google Flights to get the real, current price. If Google ever blocks the program, it uses SerpApi instead, which does the same search through an official service.
4. **It decides what counts as a deal.** Anything below the price limit is a deal. If a price is also much lower than usual for that route (25% below the typical price it has seen before), it is marked as especially good.
5. **It avoids repeating itself.** It remembers which deals it has already sent. It only mentions the same trip again if the price drops by another 10% or more.
6. **It sends one Telegram message** to our group, in French, with all the new deals ordered by date (soonest first) and a link to each flight.
7. **It saves what it learned.** The price history and the list of deals already sent are stored in `data/state.json`, which GitHub saves automatically after each run.

If a run can't get any prices at all (for example because a website changed), it sends a warning message instead of failing silently. This happens at most once a day.

### Why three price sources?

Each one covers a weakness of the others:

| Source | What it is good at | Its weak spot |
|---|---|---|
| Travelpayouts | Sees whole months of prices at once, for free | Prices can be a few hours or days old |
| Google Flights | Real, up-to-date prices, for free | It is read like a web page, so Google can block it |
| SerpApi | Reliable backup when Google fails | The free plan only allows about 250 searches a month |

## Reading the messages

Each deal in the message shows the dates, the route, the departure time, the price and the airline, plus a link to see the flight.

- A **check mark** means the price was confirmed live on Google Flights.
- A **warning sign** means it is a cached price from Travelpayouts that could not be confirmed, so it is worth double-checking before getting excited.
- A **fire symbol** means the price is much lower than usual for that route.

## Changing the settings

Everything you might want to change is in [`config.yaml`](config.yaml). You don't need to touch any Python code. After editing it, save, commit and push, and the next run will use the new settings.

Some common changes:

- **Block a weekend.** Add a line to `blocked_dates`, for example:
  `- { from: 2026-12-04, to: 2026-12-06, who: Clau }`
- **Change the price limit for visits.** Edit `max_price` under `visit`.
- **Add a meetup city.** Add a line to `meetup.destinations` with the city name, its airport code, and optionally its own price limit (`max_total`).
- **A city where Titou goes by train.** Add `paris_by_train: true, max_price: 200` to that city's line, like Amsterdam.
- **Another Spanish city Clau can reach by train.** Add its airport code to `from_paris_to` (and its name to `CITIES` in `vuelos/models.py`).
- **Other days of the week.** Edit `weekend_patterns`. Days are numbered from 0 (Monday) to 6 (Sunday).
- **The names in the messages.** Edit `people`.
- **How often it runs.** Edit the `cron` line in `.github/workflows/vuelos.yml`. Times are in UTC.

## Setting it up from scratch

This takes about 20 minutes.

**1. Create the Telegram bot.**
In Telegram, open @BotFather, send `/newbot` and follow the steps. It gives you a token: a long code that lets the program send messages as the bot. Then create a group, add the bot to it (search for its exact username, starting with @), and send `/start@your_bot_username` in the group.

**2. Get the free keys.**
Sign up at [Travelpayouts](https://www.travelpayouts.com) (under Tools, then API) and at [SerpApi](https://serpapi.com) (on the Dashboard) to get an API key from each. Both are free. The program still works without them, but with less coverage.

**3. Try it on your computer.**
Install what the program needs:
```bash
pip install -r requirements.txt
```
Create a file called `.env` in the project folder with your token:
```
TELEGRAM_BOT_TOKEN=your_token_here
```
Find out the id of your Telegram group:
```bash
python -m vuelos.telegram_setup
```
Add that id to `.env`, along with the other keys:
```
TELEGRAM_CHAT_ID=-100...
TRAVELPAYOUTS_TOKEN=...
SERPAPI_KEY=...
```
Send a test message to the group:
```bash
python -m vuelos --test-telegram
```
The `.env` file stays on your computer and is never uploaded to GitHub.

**4. Put it on GitHub.**
Push the project to a GitHub repository. Then go to Settings, Secrets and variables, Actions, and add the same four values as secrets: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TRAVELPAYOUTS_TOKEN` and `SERPAPI_KEY`. Secrets are stored safely and nobody else can see them, even if the repository is public.

**5. Start it.**
Go to the Actions tab, open "Find flight deals" and click "Run workflow". The first run takes about ten minutes. After that it runs by itself four times a day.

## Useful commands

```bash
python -m vuelos --dry-run
```
Searches for real, but prints the messages on screen instead of sending them. Good for trying out changes.

```bash
python -m vuelos --test-telegram
```
Only sends a test message, to check that Telegram is connected.

## Good to know

- **Always run `git pull` before changing anything locally.** The program saves its history to the repository after every run, so your copy gets out of date quickly. If you forget, GitHub will reject your push; just run `git pull` and push again.
- **Google may change its website at some point**, and then the Google part will stop working until the library it uses (`fast-flights`) is updated. In the meantime SerpApi takes over, and if nothing works at all you'll get a warning on Telegram.
- **Prices move fast.** When a good one shows up, it is worth booking soon.

For a longer explanation of how this was built and why each decision was made, see [GUIDE.md](GUIDE.md).
