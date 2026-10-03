# Guide: how to build this from scratch (and why it's built this way)

This guide explains the process I followed, so you can repeat it yourself with this or any other project.

---

## 0. The order of work, in short

1. **Turn the wish into concrete rules.** "Tell me about deals" can't be programmed; "return, direct, MAD→CDG/ORY, Fri/Sat→Sun/Mon, ≤ €150" can.
2. **Check the data exists** and that I can get it for free (feasibility).
3. **Test the riskiest source before writing anything else.** If I can't get prices, nothing else matters.
4. **Minimal prototype:** one route, one date, print the price.
5. **Generalise:** every route and date, plus the deal rules.
6. **Memory:** history and "already alerted".
7. **Output:** Telegram message.
8. **Automate:** make it run by itself.
9. **Harden:** what happens if something fails, if we get blocked, if alerts repeat…

---

## 1. Turning the problem into rules

Before coding, I wrote down what you asked for as rules a computer can check:

| What you said | Rule in the code |
|---|---|
| "No Ryanair to Paris because it lands in Beauvais" | Ban the **airport** BVA, not the airline (the airport is the actual problem). That also removes other airlines flying to Beauvais, and Vatry (XCR) |
| "€150 limit, return, per person" | Search **return trips** for 1 adult with price ≤ 150 |
| "No layovers" | `max_stops=0` and discard any result with more than one leg |
| "Friday or Saturday → Sunday or Monday" | Generate the 4 date combinations for each weekend |
| "I only fly from Madrid; he can fly to Valencia, Zaragoza or Barcelona and I take the train" | Two separate lists: `to_paris_from: [MAD]` and `from_paris_to: [MAD, VLC, ZAZ, BCN]` |
| "Meet somewhere else" | Both flights, **same weekend**, same destination, with the **sum** below a limit |

💡 **Lesson:** lots of software bugs come from ambiguous requirements. That's why I asked you questions at the start (is the limit return or one-way? which days?).

---

## 2. Is it doable? Where the data lives

The key question was **where do I get prices from**. There are a few kinds of source:

1. **Official aggregator APIs** (Skyscanner, Kayak…): usually only for companies or partners, not for students.
2. **Free APIs with limitations**: e.g. **Travelpayouts** (Aviasales). It's free because it makes money from affiliate commissions. The catch: its prices are what other users searched recently (cache), not live prices.
3. **Scraping a public website**: e.g. **Google Flights**. Best data, but no official API, so you have to read the website "like a browser".
4. **Paid scraping APIs**: e.g. **SerpApi**. They do the scraping and give you clean JSON. Reliable, but the free plan is small.

### How I evaluate a source
- **Search:** "flight prices API free", "google flights python", "skyscanner api free tier".
- **Check the pricing page** and the free-plan limits: how many requests a month, and whether a credit card is required.
- **Read the docs:** which parameters it accepts (can I ask for "direct only"? return trips?) and what it returns (does it give me the **airport**? Without that I can't filter out Beauvais).
- **Send a test request** with `curl` before writing code. For example, Travelpayouts without a token answered `Unauthorized`, which confirms the URL exists and only the key is missing.

### How I evaluate a free library (GitHub repository or PyPI)
With `fast-flights` I did this:
1. **On GitHub:** stars, **date of the last commit** (if a scraper hasn't been touched for a year, it's almost certainly broken), open issues like "not working since…", and the license.
2. **Install it in an isolated environment** (`python -m venv`) so it doesn't clutter my main Python.
3. **Read the installed code**, not just the README. That's how I saw version 3 had completely changed how it's used compared to what I remembered, and that it now returns airport codes (exactly what I needed).
4. **Test it live** with a real search. It failed: Google was showing the European "Before you continue" (cookies) screen. I explain this in section 5.

💡 **Lesson:** test the riskiest part first. If Google hadn't worked, the design would have been different.

---

## 3. Design decisions (and why not others)

### Why three sources instead of one?
Each one covers the others' weak spots:
- **Travelpayouts = radar.** With 1 request it sees a whole month of a route. Cheap and broad, but may be out of date.
- **Google Flights = truth.** Live price, but it takes 1 request per route and date, and if you overdo it you get blocked.
- **SerpApi = plan B.** Only used if Google fails, with a monthly counter so we stay inside the free plan.

So the radar finds cheap **candidates** and Google **confirms** only those. Much more efficient than asking Google about everything.

### Why GitHub Actions and not something else?
| Option | Problem |
|---|---|
| Your computer with a scheduled task | It has to be switched on |
| A server (VPS) | Costs money and needs maintenance |
| Cloud functions (Vercel, AWS Lambda) | Time limits, and you need a separate database |
| **GitHub Actions** | Free, built-in cron-style scheduling, secure secrets, and the repository itself works as the "database" |

### Why a JSON file in the repository instead of a database?
It's very little data (a few KB). A JSON file is human-readable, needs no extra service, and git gives you the **change history for free**. With thousands of routes I would use SQLite or Postgres.

### Why Telegram and not WhatsApp or email?
- **Telegram:** creating a bot is free, takes 2 minutes, and sending is a single HTTP request.
- **WhatsApp:** its official API is for businesses, paid, and needs approved templates.
- **Email:** gets lost among other emails and needs SMTP setup.

### Other small decisions
- **Search by airport (CDG, ORY), not by city (PAR):** "PAR" includes Beauvais. Asking for the exact airports means Beauvais never shows up. I also filter BVA out of the results just in case (double safety).
- **15 % tolerance:** if the radar says €160 and the limit is 150, I still check it, because the live price may have dropped.
- **2.5 s pause between Google searches:** so we don't look like an aggressive robot or overload anyone.
- **Group by weekend:** if MAD→CDG and MAD→ORY both show up for the same weekend, you only get alerted about the cheaper one.

---

## 4. "Which model do you use?"

**There is no artificial intelligence or machine learning.** It's **rules** plus **simple statistics**:

- **Fixed rules:** price ≤ limit? direct? not Beauvais?
- **"Usual price":** every run stores the **median** of the prices seen on each route. 🔥 = price ≤ 75 % of the historical median, and only once there are at least 5 data points.
- **Why median and not mean:** the mean shoots up with one absurd €900 Christmas price; the median doesn't.

Could ML be used to **predict** whether a price will drop? Yes, but it would need lots of history (months), and what you want (an alert when something is cheap **now**) is solved well with rules. Simple and working first; sophisticated later, if needed.

### The data model (how the information is represented)
```
Offer (one return flight)
  origin, destination, departure date, return date, price, airline,
  source (google/serpapi/travelpayouts), link,
  verified (✅ live / ⚠️ cached)

Deal (one alert)
  kind (visit to Paris / visit to Spain / meetup),
  1 Offer (visit) or 2 Offers (meetup: yours and his),
  limit, history key, 🔥?
```
Keeping "what I found" (Offer) separate from "what I alert you about" (Deal) lets a meetup be two flights added together.

---

## 5. How the Google Flights scraping works

Scraping means **reading a website with a program** instead of with your eyes. The steps to figure out how to do it on any website:

1. **Open the site in Chrome → F12 (DevTools) → Network tab.** Do a search and look at the requests that go out.
2. **Look at the URL.** Google Flights encodes the whole search in a `tfs=...` parameter. It's a **protobuf** (Google's binary format) turned into base64. `fast-flights` knows how to build it: that's its main job.
3. **Find where the data comes from.** Right click → "View page source" and search for a price you can see on screen. On Google Flights the results come inside the page itself as a block of JavaScript: `<script class="ds:1">…data:[…]</script>`. You cut out that piece and read it as JSON.
4. **Pretend to be a real browser.** Websites detect robots by how the connection "introduces itself" (TLS fingerprint and headers). `fast-flights` uses the `primp` library, which imitates Chrome.
5. **Deal with obstacles.** From Europe, Google first shows the cookie notice. I spotted it because the returned page's title was "Before you continue". I solved it by sending the "consent accepted" cookie (`SOCS`), just like your browser would after you click accept.
6. **Expect it to break.** If Google changes its website, the code that reads `ds:1` stops working. That's why:
   - the library version is pinned in `requirements.txt` (`fast-flights==3.1.0`), so it doesn't change on its own;
   - if Google fails, SerpApi is used instead;
   - if there are no prices at all, you get a Telegram warning.

⚖️ **Ethics and legality:** Google's terms don't allow automated scraping. For personal use, with few requests and pauses, the practical risk is low (at worst, a temporary IP block). I would never use this for anything commercial or large-scale; that's what APIs like SerpApi are for.

---

## 6. Things to think about (checklist)

- **Limits and costs:** requests per run × runs per day × 30. Here it's ~130 Google searches per run, 4 runs a day, and about 1,000–1,200 Actions minutes a month.
- **Silent failures:** the worst case is it stops working without you knowing. That's why there's an error warning (at most once a day).
- **Spam:** without memory it would alert you about the same flight 4 times a day. That's why it stores "already alerted at €X" and only repeats if it drops another 10 %.
- **Secrets:** keys **never** go in the code. Locally they go in `.env` (listed in `.gitignore`), and on GitHub in *Secrets*.
- **Time zones:** GitHub's cron runs in **UTC**; Madrid is +1 or +2 hours.
- **Data quality:** a cached price (⚠️) isn't the same as a checked one (✅), and the message says so.
- **Testing without bothering anyone:** `--dry-run` searches for real but sends nothing. Also, to test meetups I deliberately added a fake €60 price and checked that the system corrected it to the real one (€112).
- **Maintenance:** pinned versions, a README, and settings separated from the code (`config.yaml`) so routes can be changed without touching Python.

---

## 7. Where is the history stored?

In **`data/state.json`**, inside the repository itself. After each run, GitHub Actions makes an automatic commit ("Update price history"). It looks like this:

```json
{
  "history": {
    "visit_paris|Paris":       [["2026-10-02", 187.0], ["2026-10-03", 179.0], ...],
    "visit_spain|Barcelona":   [...],
    "meetup|Lisbon":           [...]
  },
  "alerted": {
    "visit_paris|Visit to Paris|2026-11-13|2026-11-16": {"price": 98.0, "depart": "2026-11-13"}
  },
  "serpapi": {"month": "2026-10", "used": 12}
}
```

- **`history`:** each run's median price per route (the last 120 are kept). This gives the "usual price" for 🔥.
- **`alerted`:** what you've already been told about, and at what price. Past trips are removed automatically.
- **`serpapi`:** how many SerpApi searches you've used this month.

On GitHub you can open the file and use **History** to see how prices change over time.

---

## 8. Connecting your Telegram (step by step)

1. In Telegram, search for **@BotFather** (blue tick) and send `/newbot`.
2. It asks for a name (e.g. "Flight Deals") and a username ending in `bot` (e.g. `chollos_claudia_bot`).
3. It gives you a **token** like `123456789:AAF...`.
4. Create a group with your partner and add the bot: open the bot → tap its name → **⋮ → Add to group**, or in the group use **Add members** and type the bot's exact `@username`.
5. In the group, send:
   ```
   /start@chollos_claudia_bot
   ```
   (bots in groups only "see" messages starting with `/`).
6. In the project folder, create the `.env` file:
   ```bash
   notepad .env
   ```
   Write this line (your full token, **no spaces**, all on one line) and save:
   ```
   TELEGRAM_BOT_TOKEN=123456789:AAF...
   ```
7. Get the chat id (it reads the token from `.env`):
   ```bash
   python -m vuelos.telegram_setup
   ```
   The group's id is negative (`-100...`); copy it with the minus sign.
8. Add it to `.env` as a second line:
   ```
   TELEGRAM_CHAT_ID=-100...
   ```
   and check the message arrives:
   ```bash
   python -m vuelos --test-telegram
   ```
9. On GitHub: your repository → **Settings → Secrets and variables → Actions → New repository secret**. Create `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` with those values, and the same for `TRAVELPAYOUTS_TOKEN` and `SERPAPI_KEY`.

---

## 9. Pushing to your repository

From the project folder (`Documents\GitHub\vuelos-chollos`), in a terminal:

```bash
git init -b main
```
```bash
git add .
```
```bash
git commit -m "First version of the flight deal finder"
```
```bash
git remote add origin https://github.com/ClaudiaAgromayor/vuelos-chollos.git
```
```bash
git push -u origin main
```

Before `git add`, check with `git status` that **`.env` does not show up**. If it does, don't commit.

Then: the repository's **Actions** tab → "Find flight deals" → **Run workflow**. The first run takes about 10 minutes. After that it runs by itself 4 times a day.

From then on, always run `git pull` before changing anything locally, because the bot commits the history by itself.
