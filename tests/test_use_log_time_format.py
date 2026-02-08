from __future__ import annotations

import re


def test_fmt_use_log_time_keeps_year_and_is_stable_width() -> None:
    from rightcodes_tui_dashboard.ui.app import _fmt_use_log_time

    # ISO-ish time strings should be normalized to a stable 19-char format with year.
    formatted = _fmt_use_log_time("2026-02-08T12:34:56Z")
    assert re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", formatted)
    assert len(formatted) == 19

    formatted_naive = _fmt_use_log_time("2026-02-08 12:34:56")
    assert formatted_naive == "2026-02-08 12:34:56"


def test_fmt_use_log_time_fallbacks() -> None:
    from rightcodes_tui_dashboard.ui.app import _fmt_use_log_time

    assert _fmt_use_log_time("—") == "—"
    assert _fmt_use_log_time("") == "—"
    assert _fmt_use_log_time("not-a-time") == "not-a-time"
