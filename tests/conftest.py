"""Test environment.

The gateway builds its own AIChatClient from ambient credentials, so these
have to exist before anything imports app. They are deliberately fake: no test
in this suite reaches the network.
"""

import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("SIGNALWIRE_PROJECT_ID", "test-project")
os.environ.setdefault("SIGNALWIRE_API_TOKEN", "test-token")
os.environ.setdefault("SIGNALWIRE_SPACE", "test.signalwire.com")
os.environ.setdefault("PUBLIC_URL", "https://demo.example.com")
os.environ.setdefault("CHAT_PUBLIC_KEY", "test-key")

logging.getLogger("signalwire").setLevel(logging.WARNING)
