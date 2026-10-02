"""Averigua tu TELEGRAM_CHAT_ID.

1. Escribe cualquier cosa a tu bot en Telegram (o añádelo a un grupo con tu novio y escribe allí).
2. Ejecuta:  python -m vuelos.telegram_setup <TOKEN_DEL_BOT>
"""
import sys

import requests


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    r = requests.get(f"https://api.telegram.org/bot{sys.argv[1]}/getUpdates", timeout=30).json()
    if not r.get("ok"):
        sys.exit(f"Token incorrecto: {r}")
    chats = {}
    for upd in r["result"]:
        msg = upd.get("message") or upd.get("my_chat_member") or {}
        chat = msg.get("chat")
        if chat:
            chats[chat["id"]] = chat.get("title") or chat.get("first_name") or chat.get("username")
    if not chats:
        sys.exit("No veo mensajes. Escribe algo a tu bot en Telegram y vuelve a ejecutar esto.")
    for cid, name in chats.items():
        print(f"TELEGRAM_CHAT_ID={cid}   ({name})")


if __name__ == "__main__":
    main()
