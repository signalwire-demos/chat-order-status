"""Order lookup. Deliberately small and deliberately bounded.

The agent can answer questions about orders in this book and nothing else.
That bound is the product decision, not a shortcut: this is a service agent
scoped to one job, not a general-purpose assistant.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

_DIGITS = re.compile(r"\d{3,}")


@dataclass(frozen=True)
class Order:
    number: str
    status: str
    carrier: str
    eta: str
    address: str
    items: tuple[str, ...]

    def summary(self) -> str:
        items = ", ".join(self.items)
        return (
            f"Order {self.number} ({items}) is {self.status} with {self.carrier}, "
            f"due {self.eta}, going to {self.address}."
        )


class OrderBook:
    """Orders loaded from a JSON file."""

    def __init__(self, source):
        if isinstance(source, (str, Path)):
            data = json.loads(Path(source).read_text(encoding="utf-8"))
        else:
            data = dict(source)
        self._orders = {
            str(number): Order(
                number=str(number),
                status=fields.get("status", "unknown"),
                carrier=fields.get("carrier", "unknown"),
                eta=fields.get("eta", "unknown"),
                address=fields.get("address", ""),
                items=tuple(fields.get("items", ())),
            )
            for number, fields in data.items()
        }

    def __len__(self) -> int:
        return len(self._orders)

    def __iter__(self):
        """Every order, in number order, so callers need no hardcoded list."""
        return iter(sorted(self._orders.values(), key=lambda o: o.number))

    def get(self, number: str) -> Order | None:
        return self._orders.get(str(number).strip())

    @staticmethod
    def extract_number(text: str) -> str | None:
        """Pull an order number out of what someone typed or said."""
        match = _DIGITS.search(text or "")
        return match.group(0) if match else None

    def answer(self, text: str) -> str:
        """Reply to a free-text question, or say plainly that it cannot."""
        number = self.extract_number(text)
        if number is None:
            return "I can look up an order if you give me the order number."
        order = self.get(number)
        if order is None:
            return f"I cannot find order {number}. Could you check the number?"
        return order.summary()
