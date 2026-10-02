import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SECRET_NAMES = ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "TRAVELPAYOUTS_TOKEN", "SERPAPI_KEY")


def load_dotenv(path=ROOT / ".env"):
    """Para ejecutar en local: lee claves de un .env (en GitHub vienen de los Secrets)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))


def load_config(path=None):
    load_dotenv()
    with open(path or ROOT / "config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["secrets"] = {k: os.environ.get(k, "").strip() for k in SECRET_NAMES}
    return cfg
