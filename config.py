"""Configuration, read once at import."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))

PUBLIC_URL = os.environ.get("PUBLIC_URL", "http://localhost:8080").rstrip("/")
CHAT_PUBLIC_KEY = os.environ.get("CHAT_PUBLIC_KEY", "demo-key")
CHAT_HANDLE_SECRET = os.environ.get("CHAT_HANDLE_SECRET") or None
ORDERS_FILE = Path(os.environ.get("ORDERS_FILE", ROOT / "orders.json"))

ALLOWED_ORIGINS = tuple(
    o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()
)

# The SWML the gateway always sends upstream. Never taken from the browser:
# whoever could name it would pick which agent runs and which project pays.
CONFIG_URL = f"{PUBLIC_URL}/swml"
