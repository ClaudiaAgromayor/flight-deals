"""Find your TELEGRAM_CHAT_ID.

1. Put your bot token in the .env file:  TELEGRAM_BOT_TOKEN=123456789:AAF...
2. Send /start@your_bot_username in your group (or "hi" to the bot in a private chat).
3. Run:  python -m vuelos.telegram_setup
"""
import os
import sys

import requests

from .config import load_dotenv


def main():
    load_dotenv()
    # The token comes from .env; spaces are removed in case it got split when pasting
    token = "".join(sys.argv[1:]) or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    token = token.replace(" ", "")
    if not token:
        sys.exit(__doc__)
    r = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=30).json()
    if not r.get("ok"):
        sys.exit(f"Telegram doesn't accept that token ({r.get('description')}). Check TELEGRAM_BOT_TOKEN in .env")
    chats = {}
    for upd in r["result"]:
        msg = upd.get("message") or upd.get("my_chat_member") or {}
        chat = msg.get("chat")
        if chat:
            chats[chat["id"]] = chat.get("title") or chat.get("first_name") or chat.get("username")
    if not chats:
        sys.exit("No messages yet. Send /start@your_bot_username in the group and run this again.")
    for cid, name in chats.items():
        print(f"TELEGRAM_CHAT_ID={cid}   ({name})")


if __name__ == "__main__":
    main()
