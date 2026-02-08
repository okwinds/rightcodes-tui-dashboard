from __future__ import annotations

import datetime as dt

import pytest

from rightcodes_tui_dashboard.services.calculations import (
    calculate_burn_rate,
    compute_effective_quota,
    estimate_eta,
    extract_me_balance,
    extract_model_usage_rows,
    normalize_subscriptions,
    summarize_quota,
)


def test_quota_summary_includes_items_even_if_obtained_at_unparseable() -> None:
    now = dt.datetime(2026, 2, 7, 12, 0, 0)
    raw = [
        {"tier_id": 1, "total_quota": 100, "remaining_quota": 40, "created_at": "2026-02-08T00:00:00", "reset_today": True},
        {"tier_id": 2, "total_quota": 100, "remaining_quota": 40, "created_at": "not-a-date", "reset_today": False},
    ]
    items = normalize_subscriptions(raw, now=now)
    summary = summarize_quota(items)

    assert summary.total_quota_sum == 200.0
    assert summary.remaining_sum == 80.0
    assert summary.used_sum == 120.0
    assert summary.degraded is False


def test_compute_effective_quota_matches_summary_rules() -> None:
    s_reset = normalize_subscriptions(
        [{"tier_id": 1, "total_quota": 100, "remaining_quota": 40, "reset_today": True, "created_at": "2026-02-07T00:00:00"}],
        now=dt.datetime(2026, 2, 7, 12, 0, 0),
    )[0]
    q_reset = compute_effective_quota(s_reset)
    assert q_reset is not None
    assert q_reset.total_effective == 100.0
    assert q_reset.remaining_effective == 40.0
    assert q_reset.used_effective == 60.0
    assert q_reset.used_pct == pytest.approx(0.6)

    s_not_reset = normalize_subscriptions(
        [{"tier_id": 1, "total_quota": 100, "remaining_quota": 40, "reset_today": False, "created_at": "2026-02-07T00:00:00"}],
        now=dt.datetime(2026, 2, 7, 12, 0, 0),
    )[0]
    q_not_reset = compute_effective_quota(s_not_reset)
    assert q_not_reset is not None
    assert q_not_reset.total_effective == 100.0
    assert q_not_reset.remaining_effective == 40.0
    assert q_not_reset.used_effective == 60.0
    assert q_not_reset.used_pct == pytest.approx(0.6)


def test_normalize_subscriptions_splits_obtained_and_expires_time_fields() -> None:
    now = dt.datetime(2026, 2, 7, 12, 0, 0)
    raw = [
        {
            "tier_id": 1,
            "total_quota": 100,
            "remaining_quota": 40,
            "created_at": "2026-02-07T19:20:00",
            "expired_at": "2026-03-09T19:20:00",
            "reset_today": False,
        }
    ]
    s = normalize_subscriptions(raw, now=now)[0]
    assert s.obtained_at is not None
    assert s.obtained_at.isoformat(sep=" ", timespec="minutes") == "2026-02-07 19:20"
    assert s.expires_at is not None
    assert s.expires_at.isoformat(sep=" ", timespec="minutes") == "2026-03-09 19:20"


def test_burn_rate_and_eta_normal() -> None:
    now = dt.datetime(2026, 2, 7, 12, 0, 0)
    remaining = 40.0
    buckets = [{"tokens": 10}, {"tokens": 10}, {"tokens": 10}, {"tokens": 10}, {"tokens": 10}, {"tokens": 10}]
    burn = calculate_burn_rate(buckets, window_seconds=6 * 3600)
    assert burn is not None
    assert burn.tokens_per_hour == 10.0

    eta = estimate_eta(remaining=remaining, burn_tokens_per_hour=burn.tokens_per_hour, now=now)
    assert eta == now + dt.timedelta(hours=4)


def test_eta_none_when_burn_zero_or_missing() -> None:
    now = dt.datetime(2026, 2, 7, 12, 0, 0)
    assert estimate_eta(remaining=10.0, burn_tokens_per_hour=None, now=now) is None
    assert estimate_eta(remaining=10.0, burn_tokens_per_hour=0.0, now=now) is None


def test_extract_advanced_buckets_supports_trend_key() -> None:
    from rightcodes_tui_dashboard.services.calculations import extract_advanced_buckets

    payload = {"trend": [{"tokens": 1}, {"tokens": 2}]}
    buckets = extract_advanced_buckets(payload)
    assert buckets == [{"tokens": 1}, {"tokens": 2}]


def test_extract_model_usage_rows_prefers_cost_share() -> None:
    payload = {
        "details_by_model": [
            {"model": "gpt-5.2", "total_requests": 10, "total_tokens": 100, "total_cost": 9.0},
            {"model": "gpt-5.3-codex", "total_requests": 5, "total_tokens": 50, "total_cost": 1.0},
        ]
    }
    rows = extract_model_usage_rows(payload)
    assert [r.model for r in rows] == ["gpt-5.2", "gpt-5.3-codex"]
    assert rows[0].share_basis == "cost"
    assert rows[0].share == pytest.approx(0.9)
    assert rows[1].share == pytest.approx(0.1)


def test_extract_me_balance_prefers_balance_field() -> None:
    assert extract_me_balance({"balance": 5.71234}) == pytest.approx(5.71234)


def test_extract_me_balance_parses_numeric_string() -> None:
    assert extract_me_balance({"balance": "5.700100"}) == pytest.approx(5.7001)
