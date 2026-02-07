from __future__ import annotations

from rightcodes_tui_dashboard.api.client import extract_user_token


def test_extract_user_token_user_token_variant() -> None:
    assert extract_user_token({"user_token": "abc"}) == "abc"


def test_extract_user_token_userToken_variant() -> None:
    assert extract_user_token({"userToken": "def"}) == "def"


def test_extract_user_token_missing_returns_none() -> None:
    assert extract_user_token({}) is None

