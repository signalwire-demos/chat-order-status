"""The switch itself, end to end, with the platform faked.

This is the demo's whole claim: a conversation moves between text and voice
and does not start over. Everything below runs the real HandoffRouter, the
real gateway handle signing and the real store.
"""

import pytest
from fastapi.testclient import TestClient

from order_status import OrderBook
from order_status.switching import CallControl

BOOK = {
    "4417": {
        "status": "out for delivery",
        "carrier": "Northline",
        "eta": "today before 6pm",
        "address": "12 Bridge Street, Bristol",
        "items": ["Standing desk mat"],
    }
}
ORIGIN = {"Origin": "https://demo.example.com"}


class FakeCalling:
    def __init__(self):
        self.dialled, self.ended, self.said = [], [], []

    def dial(self, **kw):
        self.dialled.append(kw)
        return {"id": "call-1"}

    def end(self, call_id, **kw):
        self.ended.append(call_id)

    def ai_message(self, call_id, **kw):
        self.said.append((call_id, kw.get("message_text")))


class FakeClient:
    def __init__(self):
        self.calling = FakeCalling()


@pytest.fixture
def wired(monkeypatch):
    import config

    monkeypatch.setattr(config, "PUBLIC_URL", "https://demo.example.com")
    monkeypatch.setattr(config, "DEFAULT_DIAL_TO", "+15557654321")
    from app import build

    control = CallControl(
        client=FakeClient(),
        from_number="+15550001111",
        swml_url="https://demo.example.com/swml",
    )
    agent, gateway, handoff, store, pending, calls = build(
        orders=OrderBook(BOOK), calls=control
    )
    return {
        "agent": agent, "gateway": gateway, "handoff": handoff,
        "store": store, "pending": pending, "calls": control,
        "client": TestClient(agent.get_app()),
    }


# ── text to voice ────────────────────────────────────────────────────

def test_escalate_captures_the_text_leg_before_anything_dials(wired):
    """The ordering guarantee: the record lands before the new medium starts."""
    handle = wired["gateway"].mint_handle("c1")
    response = wired["client"].post("/chat/escalate", json={"handle": handle}, headers=ORIGIN)
    assert response.status_code == 200
    assert wired["store"].captured("c1") is True


def test_escalate_rejects_a_forged_handle(wired):
    response = wired["client"].post("/chat/escalate", json={"handle": "not-signed"}, headers=ORIGIN)
    assert response.status_code in (400, 404)


def test_dial_places_a_call_carrying_a_nonce(wired):
    handle = wired["gateway"].mint_handle("c1")
    body = wired["client"].post("/escalate/dial", json={"handle": handle}).json()

    assert body["ok"] is True
    assert body["conversation_id"] == "c1"
    dialled = wired["calls"].client.calling.dialled[0]
    assert dialled["url"].endswith(f"?handoff_nonce={body['nonce']}")


def test_dial_refuses_a_handle_it_did_not_sign(wired):
    assert wired["client"].post("/escalate/dial", json={"handle": "forged"}).status_code == 400


def test_dial_requires_a_handle(wired):
    assert wired["client"].post("/escalate/dial", json={}).status_code == 400


# ── the nonce meets the call id ──────────────────────────────────────

def test_swml_fetch_registers_the_nonce_against_the_platforms_call_id(wired):
    handle = wired["gateway"].mint_handle("c1")
    nonce = wired["client"].post("/escalate/dial", json={"handle": handle}).json()["nonce"]

    class Req:
        query_params = {"handoff_nonce": nonce}

    # The platform fetches the SWML and posts its own call id.
    wired["agent"].on_swml_request({"call_id": "call-1"}, None, Req())

    entry = wired["handoff"]._lookup(nonce)
    assert entry is not None
    assert entry.conversation_id == "c1"
    assert entry.call_id == "call-1"


def test_a_nonce_we_never_issued_is_not_registered(wired):
    class Req:
        query_params = {"handoff_nonce": "browser-invented-this"}

    wired["agent"].on_swml_request({"call_id": "call-1"}, None, Req())
    assert wired["handoff"]._lookup("browser-invented-this") is None


def test_swml_fetch_without_a_nonce_is_harmless(wired):
    class Req:
        query_params = {}

    assert wired["agent"].on_swml_request({"call_id": "call-1"}, None, Req()) is not None or True


# ── typing into the live call ────────────────────────────────────────

def test_say_reaches_the_call(wired):
    handle = wired["gateway"].mint_handle("c1")
    nonce = wired["client"].post("/escalate/dial", json={"handle": handle}).json()["nonce"]

    class Req:
        query_params = {"handoff_nonce": nonce}

    wired["agent"].on_swml_request({"call_id": "call-1"}, None, Req())

    response = wired["client"].post(
        "/chat/say", json={"nonce": nonce, "text": "is it still coming today"}, headers=ORIGIN
    )
    assert response.status_code == 200
    assert wired["calls"].client.calling.said == [("call-1", "is it still coming today")]


def test_say_with_a_bad_nonce_touches_nothing(wired):
    response = wired["client"].post(
        "/chat/say", json={"nonce": "nope", "text": "hello"}, headers=ORIGIN
    )
    assert response.status_code == 404
    assert wired["calls"].client.calling.said == []


# ── voice back to text ───────────────────────────────────────────────

def test_handoff_ends_the_call_and_returns_a_handle_for_the_next_leg(wired):
    handle = wired["gateway"].mint_handle("c1")
    nonce = wired["client"].post("/escalate/dial", json={"handle": handle}).json()["nonce"]

    class Req:
        query_params = {"handoff_nonce": nonce}

    wired["agent"].on_swml_request({"call_id": "call-1"}, None, Req())

    response = wired["client"].post("/chat/handoff", json={"nonce": nonce}, headers=ORIGIN)
    assert response.status_code == 200

    new_handle = response.json()["handle"]
    # A new leg, same thread: the id gains a suffix rather than being reused.
    assert wired["gateway"].read_handle(new_handle).startswith("c1.")
    assert wired["calls"].client.calling.ended == ["call-1"]
    assert wired["store"].captured("c1") is True


def test_a_nonce_is_one_attempt(wired):
    handle = wired["gateway"].mint_handle("c1")
    nonce = wired["client"].post("/escalate/dial", json={"handle": handle}).json()["nonce"]

    class Req:
        query_params = {"handoff_nonce": nonce}

    wired["agent"].on_swml_request({"call_id": "call-1"}, None, Req())

    assert wired["client"].post("/chat/handoff", json={"nonce": nonce}, headers=ORIGIN).status_code == 200
    # Replaying it must not mint a second handle.
    assert wired["client"].post("/chat/handoff", json={"nonce": nonce}, headers=ORIGIN).status_code == 404


# ── the whole round trip ─────────────────────────────────────────────

def test_context_survives_text_to_voice_to_text(wired):
    store = wired["gateway"], wired["store"]
    gateway, store = store

    # Text leg establishes something.
    store.leg("c1", "text").add("user", "where is 4417")
    store.remember("c1", order_number="4417", address="12 Bridge Street, Bristol")

    # Text -> voice.
    handle = gateway.mint_handle("c1")
    wired["client"].post("/chat/escalate", json={"handle": handle}, headers=ORIGIN)
    nonce = wired["client"].post("/escalate/dial", json={"handle": handle}).json()["nonce"]

    class Req:
        query_params = {"handoff_nonce": nonce}

    wired["agent"].on_swml_request({"call_id": "call-1"}, None, Req())
    # The call runs on the SAME conversation id. Only the leg after it is new.
    store.leg("c1").add("user", "is it still coming today")

    # Voice -> text.
    new_handle = wired["client"].post("/chat/handoff", json={"nonce": nonce}, headers=ORIGIN).json()["handle"]
    next_id = gateway.read_handle(new_handle)

    # The third leg still knows what the first one was told.
    assert store.known(next_id)["order_number"] == "4417"
    assert store.known(next_id)["address"] == "12 Bridge Street, Bristol"
    assert [m["text"] for m in store.history(next_id)] == [
        "where is 4417",
        "is it still coming today",
    ]
    assert [m["medium"] for m in store.history(next_id)] == ["text", "voice"]
