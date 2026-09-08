"""Order lookup, including the cases where it must decline."""

import pytest

from order_status.orders import OrderBook

BOOK = {
    "4417": {
        "status": "out for delivery",
        "carrier": "Northline",
        "eta": "today before 6pm",
        "address": "12 Bridge Street, Bristol",
        "items": ["Standing desk mat"],
    }
}


@pytest.fixture
def orders():
    return OrderBook(BOOK)


def test_loads_orders(orders):
    assert len(orders) == 1


def test_get_returns_an_order(orders):
    assert orders.get("4417").carrier == "Northline"


def test_get_tolerates_whitespace(orders):
    assert orders.get("  4417 ") is not None


def test_unknown_order_is_none(orders):
    assert orders.get("9999") is None


def test_summary_mentions_status_and_address(orders):
    summary = orders.get("4417").summary()
    assert "out for delivery" in summary
    assert "12 Bridge Street, Bristol" in summary


@pytest.mark.parametrize(
    "text,expected",
    [
        ("where is order 4417", "4417"),
        ("4417", "4417"),
        ("order #6001 please", "6001"),
        ("no numbers here", None),
        ("only 12 two digits", None),   # too short to be an order number
        ("", None),
    ],
)
def test_extract_number(text, expected):
    assert OrderBook.extract_number(text) == expected


def test_answer_uses_the_order(orders):
    assert "out for delivery" in orders.answer("where is 4417")


def test_answer_asks_for_a_number_when_there_is_none(orders):
    assert "order number" in orders.answer("where is my stuff")


def test_answer_declines_an_unknown_order(orders):
    assert "cannot find order 9999" in orders.answer("what about 9999")


def test_loads_from_a_json_file(tmp_path):
    import json

    path = tmp_path / "orders.json"
    path.write_text(json.dumps(BOOK))
    assert len(OrderBook(path)) == 1
