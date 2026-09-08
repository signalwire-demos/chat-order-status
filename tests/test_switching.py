"""The nonce, the dial, and the two real call operations."""

import pytest

from order_status.switching import CallControl, PendingNonces, call_id_from


# ── nonces ───────────────────────────────────────────────────────────

@pytest.fixture
def pending():
    return PendingNonces()


def test_issue_returns_a_claimable_nonce(pending):
    nonce = pending.issue("c1")
    assert pending.claim(nonce) == "c1"


def test_nonces_are_unguessable_and_unique(pending):
    nonces = {pending.issue("c1") for _ in range(50)}
    assert len(nonces) == 50
    assert all(len(n) >= 24 for n in nonces)


def test_unknown_nonce_claims_nothing(pending):
    assert pending.claim("made-up") is None


@pytest.mark.parametrize("bad", [None, "", 12345, b"bytes"])
def test_rubbish_never_claims_a_conversation(pending, bad):
    assert pending.claim(bad) is None


def test_claim_does_not_consume(pending):
    """The platform may fetch the SWML more than once for one call."""
    nonce = pending.issue("c1")
    assert pending.claim(nonce) == "c1"
    assert pending.claim(nonce) == "c1"


def test_forget_removes_it(pending):
    nonce = pending.issue("c1")
    pending.forget(nonce)
    assert pending.claim(nonce) is None


def test_stale_nonces_expire():
    pending = PendingNonces(ttl=-1)   # everything is already too old
    nonce = pending.issue("c1")
    assert pending.claim(nonce) is None


def test_two_conversations_get_different_nonces(pending):
    assert pending.issue("c1") != pending.issue("c2")


# ── where the call id may come from ──────────────────────────────────

@pytest.mark.parametrize(
    "payload,expected",
    [
        ({"call_id": "abc"}, "abc"),
        ({"callId": "abc"}, "abc"),
        ({"CallSid": "abc"}, "abc"),
        ({"call": {"call_id": "abc"}}, "abc"),
        ({"call": {"id": "abc"}}, "abc"),
        ({}, None),
        (None, None),
        ({"call_id": ""}, None),
        ({"call_id": 42}, None),
    ],
)
def test_call_id_is_dug_out_of_the_platform_payload(payload, expected):
    assert call_id_from(payload) == expected


# ── call control ─────────────────────────────────────────────────────

class FakeCalling:
    def __init__(self):
        self.dialled, self.ended, self.said = [], [], []

    def dial(self, **kwargs):
        self.dialled.append(kwargs)
        return {"id": "call-1"}

    def end(self, call_id, **kwargs):
        self.ended.append(call_id)

    def ai_message(self, call_id, **kwargs):
        self.said.append((call_id, kwargs.get("message_text")))


class FakeClient:
    def __init__(self):
        self.calling = FakeCalling()


@pytest.fixture
def control():
    return CallControl(
        client=FakeClient(), from_number="+15550001111",
        swml_url="https://demo.example.com/swml",
    )


def test_can_dial_needs_all_three(control):
    assert control.can_dial is True
    assert CallControl().can_dial is False
    assert CallControl(client=FakeClient(), from_number="+1").can_dial is False


def test_dial_puts_the_nonce_in_the_swml_url(control):
    control.dial("+15557654321", "NONCE123")
    sent = control.client.calling.dialled[0]
    assert sent["url"] == "https://demo.example.com/swml?handoff_nonce=NONCE123"
    assert sent["to"] == "+15557654321"
    assert sent["from_"] == "+15550001111"


def test_end_call_reaches_the_platform(control):
    control.end_call("call-9")
    assert control.client.calling.ended == ["call-9"]


def test_send_message_reaches_the_platform(control):
    control.send_message("call-9", "is it still coming today")
    assert control.client.calling.said == [("call-9", "is it still coming today")]


def test_without_a_client_it_records_but_does_not_explode():
    control = CallControl()
    control.end_call("call-9")
    control.send_message("call-9", "hello")
    assert [c["op"] for c in control.calls] == ["end", "say"]
