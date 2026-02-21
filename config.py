import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
# No trailing slash; base URL must be reachable (DNS/network required)
_raw_base = os.getenv(
    "IPTV_BASE_URL",
    "https://iptv-be-production.up.railway.app",
).strip()
IPTV_BASE_URL = _raw_base.rstrip("/") or "https://iptv-be-production.up.railway.app"
