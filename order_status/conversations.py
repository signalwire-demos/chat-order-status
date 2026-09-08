"""What survives the move between text and voice.

`ChatGateway` and `HandoffRouter` own the wire contract: the routes, the nonce,
the ordering guarantee. They own nothing about what a conversation *is*. That
is this file, and it is the part the demo has to put on screen, because a
switch that fires proves plumbing while a switch that remembers proves the
product.

The ordering guarantee runs through `capture_leg`: a new medium never starts
until the one it replaces has finished and its record is durable. `capture_leg`
returns truthy only once that write has happened, which is what makes the wait
meaningful.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field


@dataclass
class Leg:
    """One stretch of a conversation on one medium."""

    conversation_id: str
    medium: str                       # "text" or "voice"
    messages: list[dict] = field(default_factory=list)
    captured: bool = False

    def add(self, role: str, text: str) -> None:
        """Stamp the medium now, not when the history is read.

        One conversation id hosts text and then voice: only the leg *after* a
        call gets a new id. Resolving the medium at read time therefore
        relabels every earlier message the moment the leg turns to voice.
        """
        self.messages.append({"role": role, "text": text, "medium": self.medium})


class ConversationStore:
    """Legs and collected facts, keyed by conversation id.

    Collected facts are the thing a customer notices. If they typed an address
    before switching to voice, the voice leg has to already know it.
    """

    def __init__(self):
        self._legs: dict[str, Leg] = {}
        self._facts: dict[str, dict] = {}
        self._lock = threading.Lock()

    # ── legs ─────────────────────────────────────────────────────────

    def leg(self, conversation_id: str, medium: str = "text") -> Leg:
        with self._lock:
            leg = self._legs.get(conversation_id)
            if leg is None:
                leg = Leg(conversation_id=conversation_id, medium=medium)
                self._legs[conversation_id] = leg
            return leg

    def begin(self, conversation_id: str, medium: str) -> None:
        """A new medium is starting on this conversation id.

        Called when a call is placed for a conversation that was text, so
        messages from here on are stamped as voice.
        """
        with self._lock:
            leg = self._legs.get(conversation_id)
            if leg is None:
                leg = Leg(conversation_id=conversation_id, medium=medium)
                self._legs[conversation_id] = leg
            leg.medium = medium

    def capture_leg(self, conversation_id: str, medium: str) -> bool:
        """End a leg and write its record. Truthy only once it is durable.

        HandoffRouter waits on this before it mints a handle for the new
        medium. Returning True early is how you get a new leg that opens
        knowing nothing.
        """
        with self._lock:
            leg = self._legs.get(conversation_id)
            if leg is None:
                leg = Leg(conversation_id=conversation_id, medium=medium)
                self._legs[conversation_id] = leg
            leg.medium = medium
            leg.captured = True
            return True

    def captured(self, conversation_id: str) -> bool:
        leg = self._legs.get(conversation_id)
        return bool(leg and leg.captured)

    # ── facts ────────────────────────────────────────────────────────

    def remember(self, conversation_id: str, **facts) -> dict:
        """Record what has been established, whatever medium established it."""
        root = self.root_id(conversation_id)
        with self._lock:
            known = self._facts.setdefault(root, {})
            known.update({k: v for k, v in facts.items() if v is not None})
            return dict(known)

    def known(self, conversation_id: str) -> dict:
        return dict(self._facts.get(self.root_id(conversation_id), {}))

    def history(self, conversation_id: str) -> list[dict]:
        """Every message across every leg of this conversation, in order."""
        root = self.root_id(conversation_id)
        messages: list[dict] = []
        for cid in sorted(self._legs, key=self._sort_key):
            if self.root_id(cid) == root:
                leg = self._legs[cid]
                messages += [
                    {**m, "medium": m.get("medium") or leg.medium} for m in leg.messages
                ]
        return messages

    # ── ids ──────────────────────────────────────────────────────────

    @staticmethod
    def root_id(conversation_id: str) -> str:
        """A new leg gets `.N` appended. Facts belong to the whole thread."""
        return str(conversation_id).split(".", 1)[0]

    @staticmethod
    def _sort_key(conversation_id: str):
        root, _, suffix = str(conversation_id).partition(".")
        return (root, int(suffix) if suffix.isdigit() else 0)
