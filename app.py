#!/usr/bin/env python3
"""The order desk, reachable by text and by voice, as one conversation.

    GET  /swml            the agent, for a voice call
    POST /chat            text conversation (ChatGateway JSON-RPC)
    POST /chat/handoff    voice call  -> text
    POST /chat/escalate   text        -> voice call
    POST /chat/say        type into a live call

The three handoff routes are siblings of /chat because the browser widget
derives all of them from one configured URL.

Run:
    python app.py
"""

import logging

from dotenv import load_dotenv
from signalwire.ai_chat import AIChatClient, ChatGateway, HandoffRouter

import config
from agent import OrderStatusAgent
from order_status import ConversationStore, OrderBook

load_dotenv()
logging.basicConfig(level=logging.INFO, force=True)
logger = logging.getLogger(__name__)


def build(orders=None, store=None):
    """Wire the agent, the gateway and the handoff routes together."""
    store = store or ConversationStore()
    orders = orders or OrderBook(config.ORDERS_FILE)

    agent = OrderStatusAgent(orders=orders, store=store, host=config.HOST, port=config.PORT)

    # Build the chat client explicitly rather than letting the gateway infer
    # it, so the space value is normalised in exactly one place. See config.py.
    client = AIChatClient(space=config.SPACE_NAME) if config.SPACE_NAME else None

    gateway = ChatGateway(
        config_url=config.CONFIG_URL,
        key=config.CHAT_PUBLIC_KEY,
        allowed_origins=config.ALLOWED_ORIGINS,
        secret=config.CHAT_HANDLE_SECRET,
        client=client,
    )

    handoff = HandoffRouter(
        gateway=gateway,
        # The ordering guarantee. The new medium does not start until this
        # returns, so it must not return before the record is durable.
        capture_leg=store.capture_leg,
        end_call=lambda call_id: logger.info("ending call %s", call_id),
        send_message=lambda call_id, text: logger.info("say to %s: %s", call_id, text),
    )

    # include_router(prefix="/chat") puts the gateway's "POST /" at "/chat/".
    # A POST to "/chat" with no trailing slash then falls through to the
    # agent's catch-all, which answers 200 with an error body rather than
    # 404 -- so a mis-derived widget URL looks like a working endpoint that
    # returns nonsense. Alias it before the mounts, so the catch-all (which
    # each mount pushes back to the end) never sees it.
    fastapi_app = agent.get_app()

    @fastapi_app.post("/chat", include_in_schema=False)
    @fastapi_app.options("/chat", include_in_schema=False)
    async def _chat_no_trailing_slash():
        from fastapi.responses import RedirectResponse

        return RedirectResponse("/chat/", status_code=307)

    # What the agent has established, whichever medium established it. The
    # page renders this so a viewer can watch it survive the switch, which is
    # the difference between proving plumbing and proving the product.
    @fastapi_app.get("/state/{conversation_id}", include_in_schema=False)
    async def _state(conversation_id: str):
        return {
            "conversation_id": conversation_id,
            "root": store.root_id(conversation_id),
            "known": store.known(conversation_id),
            "history": store.history(conversation_id),
            "captured": store.captured(conversation_id),
        }

    agent.mount(gateway.router(), prefix="/chat")
    agent.mount(handoff.router(), prefix="/chat")

    from fastapi.staticfiles import StaticFiles

    agent.mount(StaticFiles(directory=str(config.ROOT / "web"), html=True), prefix="/demo")

    return agent, gateway, handoff, store


agent, gateway, handoff, store = build()
app = agent.get_app()

if __name__ == "__main__":
    agent.serve()
