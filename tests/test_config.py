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
