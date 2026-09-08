"""SIGNALWIRE_SPACE is read two different ways by the SDK. Normalise both."""

import pytest

import config


@pytest.mark.parametrize(
    "given,name,host",
    [
        ("briankwest", "briankwest", "briankwest.signalwire.com"),
        ("briankwest.signalwire.com", "briankwest", "briankwest.signalwire.com"),
        ("briankwest.signalwire.me", "briankwest", "briankwest.signalwire.me"),
        ("", "", ""),
    ],
)
def test_space_is_normalised_from_either_form(given, name, host):
    assert config.space_name(given) == name
    assert config.space_host(given) == host


def test_bare_name_never_gets_the_domain_twice():
    # The failure this guards: briankwest.signalwire.com.signalwire.com
    assert config.space_host("briankwest.signalwire.com").count("signalwire.com") == 1


# ── the SWML config URL ──────────────────────────────────────────────

def test_config_url_without_credentials_is_plain():
    assert config.config_url("https://x.example.com") == "https://x.example.com/swml"


def test_config_url_embeds_credentials():
    url = config.config_url("https://x.example.com", "agent", "s3cret")
    assert url == "https://agent:s3cret@x.example.com/swml"


def test_config_url_escapes_credentials():
    # An unescaped @ or : in the password silently breaks the URL's authority.
    url = config.config_url("https://x.example.com", "a@b", "p:w@rd")
    assert url == "https://a%40b:p%3Aw%40rd@x.example.com/swml"


def test_config_url_needs_both_halves():
    assert "@" not in config.config_url("https://x.example.com", "agent", "")
    assert "@" not in config.config_url("https://x.example.com", "", "s3cret")
