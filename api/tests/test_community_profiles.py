"""Nickname and city rules (pure functions, no database)."""

from __future__ import annotations

import pytest

from pharmashed_api.community.profiles import (
    CITIES, RESERVED_NICKNAMES, InvalidNickname, InvalidProfile, validate_city, validate_nickname,
)


@pytest.mark.parametrize("name", ["Pat", "river-watcher", "Stream_Fan_99", "a1b", "x" * 20, "  Padded  "])
def test_good_nicknames_are_accepted_and_trimmed(name):
    assert validate_nickname(name) == name.strip()


@pytest.mark.parametrize("name, fragment", [
    ("ab", "3 to 20"),
    ("x" * 21, "3 to 20"),
    ("", "3 to 20"),
    ("has space", "only letters"),
    ("emoji🙂name", "only letters"),
    ("-leading", "start with"),
    ("_leading", "start with"),
    ("a@b.com", "only letters"),
    ("12345", "at least one letter"),
])
def test_bad_nicknames_are_rejected_with_a_readable_reason(name, fragment):
    with pytest.raises(InvalidNickname, match=fragment):
        validate_nickname(name)


@pytest.mark.parametrize("name", sorted(RESERVED_NICKNAMES - {"me", "you"}))
def test_names_that_could_pass_for_staff_are_reserved_in_any_case(name):
    with pytest.raises(InvalidNickname, match="reserved"):
        validate_nickname(name.upper() if len(name) >= 3 else name + "xx")


def test_cities_are_the_five_in_the_project():
    assert set(CITIES) == {"TLS", "GNT", "BNV", "CBR", "OSL"}
    assert validate_city("TLS") == "TLS" and validate_city(None) is None and validate_city("") is None
    with pytest.raises(InvalidProfile):
        validate_city("PAR")
