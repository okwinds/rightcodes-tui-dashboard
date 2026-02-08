from __future__ import annotations

from rightcodes_tui_dashboard.services.use_logs import (
    extract_use_log_billing_rate,
    extract_use_log_billing_source,
    extract_use_log_channel,
    extract_use_log_ip,
    extract_use_log_tokens,
    format_billing_rate,
    format_billing_source,
)


def test_extract_use_log_tokens_from_usage_total_tokens() -> None:
    item = {"usage": {"total_tokens": 123}}
    assert extract_use_log_tokens(item) == 123.0


def test_extract_use_log_tokens_from_usage_total_tokens_string() -> None:
    item = {"usage": {"total_tokens": "1,234"}}
    assert extract_use_log_tokens(item) == 1234.0


def test_extract_use_log_channel_prefers_upstream_prefix() -> None:
    item = {"upstream_prefix": "/codex", "channel": "other"}
    assert extract_use_log_channel(item) == "/codex"


def test_extract_use_log_billing_rate_from_billing_rate() -> None:
    item = {"billing_rate": 1.0}
    assert extract_use_log_billing_rate(item) == 1.0
    assert format_billing_rate(extract_use_log_billing_rate(item)) == "x1.00"


def test_extract_use_log_billing_source_and_format() -> None:
    item = {"billing_source": "subscription"}
    assert extract_use_log_billing_source(item) == "subscription"
    assert format_billing_source(extract_use_log_billing_source(item)) == "套餐"


def test_extract_use_log_ip() -> None:
    item = {"ip": "1.2.3.4"}
    assert extract_use_log_ip(item) == "1.2.3.4"

