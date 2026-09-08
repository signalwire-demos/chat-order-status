"""Moving one conversation between text and voice.

`HandoffRouter` owns the wire contract. What it does not own, and what this
file supplies, is the half that is the application's:

  * minting a nonce and remembering which conversation it belongs to
  * actually placing the call that carries it
  * actually ending a call and actually typing into one

The nonce is the security property. A browser cannot be trusted to name a
call, so it never does: we generate the nonce, put it in the SWML URL the
platform fetches, and read the call id out of the platform's own request.
The browser only ever presents the nonce back to us.
"""

from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass

# A nonce is only alive between placing a call and the platform fetching the
# SWML for it. Seconds, not minutes.
DEFAULT_TTL = 300.0


@dataclass
class Pending:
    conversation_id: str
    issued_at: float


class PendingNonces:
    """Nonces issued for calls that have not fetched their SWML yet."""

    def __init__(self, ttl: float = DEFAULT_TTL):
        self.ttl = ttl
        self._pending: dict[str, Pending] = {}
        self._lock = threading.Lock()

    def issue(self, conversation_id: str) -> str:
        """Mint a nonce for a conversation about to be dialled."""
        nonce = secrets.token_urlsafe(24)
        with self._lock:
            self._prune()
            self._pending[nonce] = Pending(conversation_id, time.monotonic())
        return nonce

    def claim(self, nonce: str) -> str | None:
        """The conversation a nonce belongs to, or None if unknown or stale.

        Does not consume: the platform can fetch the SWML more than once, and
        each fetch has to be able to register the same nonce.
        """
        if not nonce or not isinstance(nonce, str):
            return None
        with self._lock:
            self._prune()
            entry = self._pending.get(nonce)
            return entry.conversation_id if entry else None

    def forget(self, nonce: str) -> None:
        with self._lock:
            self._pending.pop(nonce, None)

    def __len__(self) -> int:
        with self._lock:
            self._prune()
            return len(self._pending)

    def _prune(self) -> None:
        cutoff = time.monotonic() - self.ttl
        for nonce in [n for n, e in self._pending.items() if e.issued_at < cutoff]:
            self._pending.pop(nonce, None)


class CallControl:
    """The three real call operations, behind one seam so tests can watch them.

    Without a client these become no-ops that record what they were asked to
    do, which is what the test suite and a credential-less boot both need.
    """

    def __init__(self, client=None, from_number: str = "", swml_url: str = ""):
        self.client = client
        self.from_number = from_number
        self.swml_url = swml_url
        self.calls: list[dict] = []

    @property
    def can_dial(self) -> bool:
        return bool(self.client and self.from_number and self.swml_url)

    def dial(self, to: str, nonce: str) -> dict:
        """Place a call whose SWML URL carries the nonce."""
        url = f"{self.swml_url}?handoff_nonce={nonce}"
        record = {"op": "dial", "to": to, "url": url}
        self.calls.append(record)
        if self.client:
            result = self.client.calling.dial(from_=self.from_number, to=to, url=url)
            record["result"] = result
        return record

    def end_call(self, call_id: str) -> None:
        self.calls.append({"op": "end", "call_id": call_id})
        if self.client:
            self.client.calling.end(call_id)

    def send_message(self, call_id: str, text: str) -> None:
        self.calls.append({"op": "say", "call_id": call_id, "text": text})
        if self.client:
            self.client.calling.ai_message(call_id, role="user", message_text=text)


def call_id_from(request_data: dict | None) -> str | None:
    """Dig the call id out of whatever shape the platform sent.

    Never taken from the browser. The platform posts this to the SWML URL, so
    it is the one trustworthy source for which call a nonce belongs to.
    """
    data = request_data or {}
    for key in ("call_id", "callId", "CallSid"):
        value = data.get(key)
        if isinstance(value, str) and value:
            return value
    call = data.get("call")
    if isinstance(call, dict):
        for key in ("call_id", "id", "callId"):
            value = call.get(key)
            if isinstance(value, str) and value:
                return value
    return None
