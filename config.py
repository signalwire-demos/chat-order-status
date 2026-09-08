"""Configuration, read once at import."""

import os
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))

PUBLIC_URL = os.environ.get("PUBLIC_URL", "http://localhost:8080").rstrip("/")
CHAT_PUBLIC_KEY = os.environ.get("CHAT_PUBLIC_KEY", "demo-key")
CHAT_HANDLE_SECRET = os.environ.get("CHAT_HANDLE_SECRET") or None
ORDERS_FILE = Path(os.environ.get("ORDERS_FILE", ROOT / "orders.json"))

# The SDK reads SIGNALWIRE_SPACE two different ways and neither is wrong:
# the REST HttpClient builds "https://{host}" and wants the full host, while
# AIChatClient builds "https://{space}.signalwire.com" and wants the bare
# name. Set the full host and AI Chat talks to
# briankwest.signalwire.com.signalwire.com; set the bare name and REST loses
# its domain. So accept either and derive both.
SIGNALWIRE_SPACE = os.environ.get("SIGNALWIRE_SPACE", "").strip()


def space_name(value: str) -> str:
    """The bare space name, e.g. briankwest."""
    return (value or "").strip().split(".", 1)[0]


def space_host(value: str) -> str:
    """The full host, e.g. briankwest.signalwire.com."""
    raw = (value or "").strip()
    if not raw:
        return ""
    return raw if "." in raw else f"{raw}.signalwire.com"


SPACE_NAME = space_name(SIGNALWIRE_SPACE)
SPACE_HOST = space_host(SIGNALWIRE_SPACE)

ALLOWED_ORIGINS = tuple(
    o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()
)

# The agent's /swml route is behind basic auth, and the AI Chat service
# fetches config_url with no credentials of its own, so an unauthenticated URL
# comes back 401 and the gateway answers "Configuration error" with nothing
# saying why. Embed the credentials when they are set.
SWML_BASIC_AUTH_USER = os.environ.get("SWML_BASIC_AUTH_USER", "")
SWML_BASIC_AUTH_PASSWORD = os.environ.get("SWML_BASIC_AUTH_PASSWORD", "")


def config_url(public_url: str, user: str = "", password: str = "") -> str:
    """The SWML URL the gateway sends upstream, with credentials if we have them."""
    if not (user and password):
        return f"{public_url}/swml"
    scheme, _, rest = public_url.partition("://")
    creds = f"{quote(user, safe='')}:{quote(password, safe='')}"
    return f"{scheme}://{creds}@{rest}/swml"


# Never taken from the browser: whoever could name it would pick which agent
# runs and which project pays.
CONFIG_URL = config_url(PUBLIC_URL, SWML_BASIC_AUTH_USER, SWML_BASIC_AUTH_PASSWORD)
