"""Brand compliance.

The SignalWire palette is locked. These fail if a page drifts off it, which is
the failure mode nobody notices until a screenshot goes in a deck.
"""

import re

import pytest

LOCKED = {"#044EF4", "#F72A72", "#40E0D0", "#FFD700", "#601BE6"}
# The neutral surfaces and foregrounds the system defines.
ALLOWED_NEUTRALS = {
    "#0e0e18", "#181a28", "#222436", "#1e1e1f",
    "#f0f0f4", "#e8e8ec", "#a0a0aa", "#73737e", "#d4d4d8", "#898995",
    "#FAFBFC", "#F3F4F6", "#E8EAF0", "#1A1A18", "#3A3A38", "#737371", "#070c2d",
    "#0342cf", "#fff", "#ffffff",
}
HEX = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")


def _hexes(body: str) -> set[str]:
    return {h for h in HEX.findall(body)}


def assert_on_brand(body: str):
    used = _hexes(body)
    allowed = {c.lower() for c in LOCKED | ALLOWED_NEUTRALS}
    stray = {h for h in used if h.lower() not in allowed}
    assert not stray, f"off-palette colours: {sorted(stray)}"


def assert_typography(body: str):
    for family in ("Instrument Sans", "Lexend", "JetBrains Mono"):
        assert family in body, f"{family} not declared"
    assert "Outfit" not in body, "Outfit is deprecated"


def assert_themes(body: str):
    # Dark is primary; light must be an explicit adaptation, not an omission.
    assert "--bg-page:#0e0e18" in body.replace(" ", "")
    assert "prefers-color-scheme:light" in body.replace(" ", "")


def assert_headings_are_neutral(body: str):
    # Headings take fg-headings. Colouring them is the most common brand slip.
    for rule in re.findall(r"h1[^{]*\{[^}]*\}", body):
        assert "#F72A72" not in rule and "#044EF4" not in rule, f"coloured heading: {rule}"
