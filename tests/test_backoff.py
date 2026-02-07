from __future__ import annotations

import datetime as dt
import random


def test_backoff_delay_is_exponential_with_jitter() -> None:
    from rightcodes_tui_dashboard.services.backoff import compute_next_retry_at

    rng = random.Random(0)
    now = dt.datetime(2026, 2, 7, 12, 0, 0)

    # attempt=1 -> base_delay * 2^(attempt-1) = base_delay
    next1 = compute_next_retry_at(
        now=now,
        attempt=1,
        base_delay_seconds=5,
        max_delay_seconds=60,
        rng=rng,
    )
    assert next1 > now
    assert 5 <= (next1 - now).total_seconds() <= 10

    # attempt=2 -> 10s + jitter(0..5)
    next2 = compute_next_retry_at(
        now=now,
        attempt=2,
        base_delay_seconds=5,
        max_delay_seconds=60,
        rng=random.Random(0),
    )
    assert 10 <= (next2 - now).total_seconds() <= 15


def test_backoff_caps_at_max_delay() -> None:
    from rightcodes_tui_dashboard.services.backoff import compute_next_retry_at

    now = dt.datetime(2026, 2, 7, 12, 0, 0)
    next_retry = compute_next_retry_at(
        now=now,
        attempt=99,
        base_delay_seconds=5,
        max_delay_seconds=60,
        rng=random.Random(0),
    )
    assert 60 <= (next_retry - now).total_seconds() <= 65

