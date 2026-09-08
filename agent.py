#!/usr/bin/env python3
"""One agent definition. Voice and text both run it."""

import logging

from signalwire.core.agent_base import AgentBase

import config
from order_status import ConversationStore, OrderBook

logger = logging.getLogger(__name__)


class OrderStatusAgent(AgentBase):
    """A service agent scoped to one job: where is my order."""

    def __init__(self, orders=None, store=None, **kwargs):
        super().__init__(name="order-status", route="/swml", **kwargs)
        self.orders = orders if orders is not None else OrderBook(config.ORDERS_FILE)
        self.store = store if store is not None else ConversationStore()

        self.prompt_add_section(
            "Personality",
            "You are the order desk for a furniture retailer. You are brief and exact.",
        )
        self.prompt_add_section("Rules", body="", bullets=[
            "Answer only questions about order status, delivery dates and delivery address.",
            "Always call lookup_order before stating anything about an order.",
            "Never guess an order number. Ask for it.",
            "If asked about anything else, say that you only handle order status.",
        ])
        self.set_post_prompt("Summarize what the customer asked and what was resolved.")

        self.define_tool(
            name="lookup_order",
            description="Look up an order by its number.",
            parameters={
                "order_number": {
                    "type": "string",
                    "description": "The order number, digits only.",
                }
            },
            handler=self._lookup,
            secure=False,
        )

    def _lookup(self, args, raw):
        number = (args or {}).get("order_number", "")
        order = self.orders.get(number)
        if order is None:
            return {"response": f"No order {number} found."}

        # Remember it, so the other medium already knows.
        conversation_id = (raw or {}).get("conversation_id") or (raw or {}).get("call_id")
        if conversation_id:
            self.store.remember(
                conversation_id,
                order_number=order.number,
                address=order.address,
            )
        return {"response": order.summary()}
