"""Uso:
    python -m vuelos                  # busca y avisa por Telegram
    python -m vuelos --dry-run        # busca e imprime los mensajes, sin enviar nada
    python -m vuelos --test-telegram  # solo manda un mensaje de prueba
"""
import argparse
import sys
from datetime import date

from . import telegram
from .config import load_config
from .engine import Engine
from .state import load_state, mark_alerted, save_state, select_new


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # tildes y emojis también en la consola de Windows
    ap =argparse.ArgumentParser(description="Buscador de chollos de vuelos")
    ap.add_argument("--dry-run", action="store_true", help="no envía nada a Telegram ni marca avisos")
    ap.add_argument("--no-google", action="store_true", help="no usar Google Flights (solo radar + SerpApi)")
    ap.add_argument("--test-telegram", action="store_true", help="manda un mensaje de prueba y sale")
    args = ap.parse_args()

    cfg = load_config()
    sec = cfg["secrets"]
    can_send = sec["TELEGRAM_BOT_TOKEN"] and sec["TELEGRAM_CHAT_ID"]
    if not args.dry_run and not can_send:
        sys.exit("Faltan TELEGRAM_BOT_TOKEN y/o TELEGRAM_CHAT_ID (o usa --dry-run)")

    def notify(text):
        if args.dry_run:
            print("\n──── Telegram ────\n" + text)
        else:
            telegram.send(sec["TELEGRAM_BOT_TOKEN"], sec["TELEGRAM_CHAT_ID"], text)

    if args.test_telegram:
        notify("👋 ¡Hola! El buscador de chollos de vuelos ya puede escribirte.")
        return

    state = load_state()
    engine = Engine(cfg, state, use_google=not args.no_google)
    deals = engine.run()
    new = select_new(deals, state, cfg["alerts"]["realert_drop"])[: cfg["alerts"]["max_per_message"]]
    print(f"· {len(new)} chollos nuevos para avisar")

    if new:
        for msg in telegram.build_messages(new):
            notify(msg)
        if not args.dry_run:
            mark_alerted(new, state)

    # Si no hemos podido mirar nada, avisamos (máximo una vez al día) para que no falle en silencio
    today = date.today().isoformat()
    if not engine.offers and engine.errors and state.get("last_error_notice") != today:
        notify("⚠️ <b>El buscador de vuelos no ha podido consultar precios</b>\n"
               + "\n".join(f"• {e}" for e in dict.fromkeys(engine.errors)))
        if not args.dry_run:
            state["last_error_notice"] = today

    if not args.dry_run:
        save_state(state)


if __name__ == "__main__":
    main()
