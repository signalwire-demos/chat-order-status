"""The wiring: agent, gateway and the three handoff routes, against the real SDK."""

import os

import pytest

os.environ.setdefault("PUBLIC_URL", "https://demo.example.com")
os.environ.setdefault("CHAT_PUBLIC_KEY", "test-key")

from app import build  # noqa: E402
from order_status import OrderBook  # noqa: E402

BOOK = {
    "4417": {
        "status": "out for delivery",
        "carrier": "Northline",
        "eta": "today before 6pm",
        "address": "12 Bridge Street, Bristol",
        "items": ["Standing desk mat"],
    }
}


@pytest.fixture(scope="module")
def built():
    return build(orders=OrderBook(BOOK))


@pytest.fixture(scope="module")
def client(built):
    from fastapi.testclient import TestClient

    return TestClient(built[0].get_app())


def test_agent_serves_swml(built, client):
    user, password = built[0].get_basic_auth_credentials()
    assert client.get("/swml", auth=(user, password)).status_code == 200


def test_swml_requires_auth(client):
    assert client.get("/swml").status_code == 401


@pytest.mark.parametrize("route", ["/chat/handoff", "/chat/escalate", "/chat/say"])
def test_handoff_routes_are_siblings_of_the_gateway(client, route):
    """The three routes must be mounted, and must answer as themselves.

    The widget derives every path from one configured URL, so they have to be
    siblings of the gateway. Mount them apart and the gateway answers JSON-RPC
    while these fall through to the agent's catch-all, which returns 200 and
    an error body. Rejecting an empty request is correct; being swallowed by
    the catch-all is the bug.
    """
    response = client.post(route, json={})
    assert response.json() != {"error": "Invalid route"}


def test_gateway_answers_on_the_trailing_slash(client):
    # A bare key with no upstream reachable still gets past routing, which is
    # all this asserts: the gateway, not the catch-all, is handling it.
    response = client.post("/chat/", json={}, headers={"Authorization": "Bearer test-key"})
    assert response.json() != {"error": "Invalid route"}


def test_chat_without_trailing_slash_redirects_rather_than_falling_through(client):
    # Without the alias this returns 200 {"error": "Invalid route"} from the
    # agent's catch-all, which looks like a working endpoint talking nonsense.
    response = client.post("/chat", json={}, follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"].endswith("/chat/")


def test_gateway_never_takes_the_config_url_from_the_browser(built):
    _, gateway, _, _ = built
    assert gateway.config_url == "https://demo.example.com/swml"


def test_handoff_waits_on_capture(built):
    _, _, handoff, store = built
    # capture_leg is the ordering guarantee. Omit it and no wait happens: the
    # new medium's config fetch races a record that is still seconds away.
    assert handoff.capture_leg is not None
    assert handoff.capture_leg("ordering-check", "text") is True
    assert store.captured("ordering-check") is True


# ── the agent definition ─────────────────────────────────────────────

def test_one_definition_declares_the_lookup_tool(built):
    agent = built[0]
    # AgentBase builds its SWML per request, so render_document() is empty.
    doc = agent._render_swml()
    assert "lookup_order" in (doc if isinstance(doc, str) else str(doc))


def test_lookup_returns_the_order(built):
    agent = built[0]
    reply = agent._lookup({"order_number": "4417"}, {"conversation_id": "c1"})
    assert "out for delivery" in reply["response"]


def test_lookup_declines_an_unknown_order(built):
    agent = built[0]
    assert "No order 9999 found" in agent._lookup({"order_number": "9999"}, {})["response"]


def test_lookup_remembers_for_the_other_medium(built):
    agent, _, _, store = built
    agent._lookup({"order_number": "4417"}, {"conversation_id": "c9"})
    # The voice leg that replaces this one opens already knowing the address.
    assert store.known("c9.1")["address"] == "12 Bridge Street, Bristol"


def test_lookup_without_a_conversation_id_does_not_raise(built):
    agent = built[0]
    assert agent._lookup({"order_number": "4417"}, {})["response"]


# ── the landing page ─────────────────────────────────────────────────

def test_root_is_not_the_catch_all(client):
    """/ used to return 200 {"error": "Invalid route"}, which reads as broken."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Invalid route" not in response.text


def test_root_lists_the_routes_it_documents(client):
    body = client.get("/").text
    for path in ("/demo/", "/state/", "/swml", "/chat/", "/chat/handoff", "/chat/escalate", "/chat/say"):
        assert path in body


def test_root_lists_the_orders(client):
    body = client.get("/").text
    for number in ("4417", "5120", "6001"):
        assert number in body


def test_root_is_honest_about_what_is_untested(client):
    # The switch is the hero of this demo and it has not run end to end.
    assert "not exercised" in client.get("/").text


def test_health_route(client):
    assert client.get("/health").json()["status"] == "healthy"
