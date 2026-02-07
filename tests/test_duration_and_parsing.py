from __future__ import annotations

import pytest


def test_parse_duration_seconds_supports_days() -> None:
    from rightcodes_tui_dashboard.cli import _parse_duration_seconds

    assert _parse_duration_seconds("7d") == 7 * 24 * 3600
    assert _parse_duration_seconds("1d") == 24 * 3600


def test_parse_duration_seconds_rejects_unknown_suffix() -> None:
    from rightcodes_tui_dashboard.cli import _parse_duration_seconds

    with pytest.raises(ValueError):
        _parse_duration_seconds("10w")


def test_extract_stats_totals_variants() -> None:
    from rightcodes_tui_dashboard.services.calculations import extract_stats_totals

    out = extract_stats_totals(
        {
            "total_tokens": 123,
            "total_cost": 1.25,
            "total_requests": 9,
        }
    )
    assert out.tokens == 123.0
    assert out.cost == 1.25
    assert out.requests == 9.0

    out2 = extract_stats_totals({"tokens": 7, "amount": 0.5, "request_count": 2})
    assert out2.tokens == 7.0
    assert out2.cost == 0.5
    assert out2.requests == 2.0


def test_extract_use_logs_items_variants() -> None:
    from rightcodes_tui_dashboard.services.calculations import extract_use_logs_items

    assert extract_use_logs_items({"items": [{"a": 1}]}) == [{"a": 1}]
    assert extract_use_logs_items({"logs": [{"a": 1}]}) == [{"a": 1}]
    assert extract_use_logs_items({"data": [{"a": 1}]}) == [{"a": 1}]
    assert extract_use_logs_items({"items": [1, 2, 3]}) == []


def test_redact_sensitive_fields_case_insensitive() -> None:
    from rightcodes_tui_dashboard.privacy import redact_sensitive_fields

    out = redact_sensitive_fields(
        {
            "token": "abc",
            "userToken": "def",
            "ip_address": "1.2.3.4",
            "safe": 1,
        }
    )
    assert out["safe"] == 1
    assert out["token"] == "***REDACTED***"
    assert out["userToken"] == "***REDACTED***"
    assert out["ip_address"] == "***REDACTED***"

