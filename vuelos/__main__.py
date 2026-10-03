"""Usage:
    python -m vuelos                  # search and send alerts to Telegram
    python -m vuelos --dry-run        # search and print the messages, without sending anything
    python -m vuelos --test-telegram  # only send a test message
"""
import argparse
import sys
from datetime import date

from . import telegram
from .config import load_config
from .engine import Engine
from .state import load_state, mark_alerted, save_state, select_new


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # emojis also in the Windows console
    ap = argparse.ArgumentParser(description="Cheap flight deal finder")
    ap.add_argument("--dry-run", action="store_true", help="don't send anything to Telegram or mark alerts")
    ap.add_argument("--no-google", action="store_true", help="don't use Google Flights (only radar + SerpApi)")
    ap.add_argument("--test-telegram", action="store_true", help="send a test message and exit")
    args = ap.parse_args()

    cfg = load_config()
    sec = cfg["secrets"]
    can_send = sec["TELEGRAM_BOT_TOKEN"] and sec["TELEGRAM_CHAT_ID"]
    if not args.dry_run and not can_send:
        sys.exit("TELEGRAM_BOT_TOKEN and/or TELEGRAM_CHAT_ID missing (or use --dry-run)")

    def notify(text):
        if args.dry_run:
            print("\n──── Telegram ────\n" + text)
        else:
            telegram.send(sec["TELEGRAM_BOT_TOKEN"], sec["TELEGRAM_CHAT_ID"], text)

    if args.test_telegram:
        notify("👋 Coucou ! Le chercheur de bons plans vols peut maintenant vous écrire.")
        return

    state = load_state()
    engine = Engine(cfg, state, use_google=not args.no_google)
    deals = engine.run()
    # Pick the best deals first (🔥 and cheapest), then show them by date, soonest first
    new = select_new(deals, state, cfg["alerts"]["realert_drop"])[: cfg["alerts"]["max_per_message"]]
    new.sort(key=lambda d: (d.depart, d.ret, d.total))
    print(f"· {len(new)} new deals to send")

    if new:
        for msg in telegram.build_messages(new, cfg["people"]):
            notify(msg)
        if not args.dry_run:
            mark_alerted(new, state)

    # If we couldn't check anything, say so (at most once a day) so it never fails silently
    today = date.today().isoformat()
    if not engine.offers and engine.errors and state.get("last_error_notice") != today:
        notify("⚠️ <b>Le chercheur de vols n'a pu récupérer aucun prix</b>\n"
               + "\n".join(f"• {e}" for e in dict.fromkeys(engine.errors)))
        if not args.dry_run:
            state["last_error_notice"] = today

    if not args.dry_run:
        save_state(state)


if __name__ == "__main__":
    main()
