"""The state that has to survive the switch."""

import pytest

from order_status.conversations import ConversationStore


@pytest.fixture
def store():
    return ConversationStore()


# ── the ordering guarantee ───────────────────────────────────────────

def test_capture_leg_reports_durable(store):
    assert store.capture_leg("c1", "text") is True
    assert store.captured("c1") is True


def test_uncaptured_leg_reports_false(store):
    store.leg("c1")
    assert store.captured("c1") is False


def test_capture_leg_works_for_a_leg_never_seen(store):
    assert store.capture_leg("brand-new", "voice") is True


def test_capture_leg_records_the_medium(store):
    store.capture_leg("c1", "voice")
    assert store.leg("c1").medium == "voice"


# ── facts crossing the switch ────────────────────────────────────────

def test_facts_are_remembered(store):
    store.remember("c1", order_number="4417")
    assert store.known("c1")["order_number"] == "4417"


def test_facts_survive_into_the_next_leg(store):
    # Typed in chat...
    store.remember("c1", address="12 Bridge Street, Bristol")
    store.capture_leg("c1", "text")
    # ...and the voice leg that replaces it already knows.
    assert store.known("c1.1")["address"] == "12 Bridge Street, Bristol"


def test_facts_accumulate_across_legs(store):
    store.remember("c1", order_number="4417")
    store.remember("c1.1", address="12 Bridge Street, Bristol")
    known = store.known("c1.2")
    assert known == {
        "order_number": "4417",
        "address": "12 Bridge Street, Bristol",
    }


def test_none_values_do_not_erase_a_known_fact(store):
    store.remember("c1", order_number="4417")
    store.remember("c1", order_number=None)
    assert store.known("c1")["order_number"] == "4417"


def test_separate_conversations_do_not_share_facts(store):
    store.remember("c1", order_number="4417")
    assert store.known("c2") == {}


# ── history ──────────────────────────────────────────────────────────

def test_history_spans_legs_in_order(store):
    store.leg("c1", "text").add("user", "where is 4417")
    store.capture_leg("c1", "text")
    store.leg("c1.1", "voice").add("user", "is it still coming today")
    texts = [m["text"] for m in store.history("c1.1")]
    assert texts == ["where is 4417", "is it still coming today"]


def test_history_records_which_medium_each_message_came_from(store):
    store.leg("c1", "text").add("user", "typed")
    store.leg("c1.1", "voice").add("user", "spoken")
    assert [m["medium"] for m in store.history("c1")] == ["text", "voice"]


def test_history_orders_legs_numerically_not_alphabetically(store):
    for suffix in ["", ".2", ".10"]:
        store.leg(f"c1{suffix}", "text").add("user", suffix or "first")
    assert [m["text"] for m in store.history("c1")] == ["first", ".2", ".10"]


def test_history_excludes_other_conversations(store):
    store.leg("c1").add("user", "mine")
    store.leg("c2").add("user", "theirs")
    assert [m["text"] for m in store.history("c1")] == ["mine"]


# ── ids ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "cid,root", [("c1", "c1"), ("c1.1", "c1"), ("c1.10", "c1"), ("abc", "abc")]
)
def test_root_id(cid, root):
    assert ConversationStore.root_id(cid) == root
