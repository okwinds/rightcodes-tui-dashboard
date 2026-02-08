from __future__ import annotations

import datetime as dt

from rich.console import Console

from rightcodes_tui_dashboard.services.calculations import BurnRate
from rightcodes_tui_dashboard.ui.app import DashboardScreen


def test_burn_eta_block_contains_github_and_invite_code() -> None:
    now = dt.datetime(2026, 2, 8, 0, 0, 0)
    screen = DashboardScreen(
        base_url="https://example.invalid",
        token="t",
        watch_seconds=None,
        range_seconds=24 * 3600,
        range_mode="24h",
        rate_window_seconds=6 * 3600,
        granularity="hour",
    )

    screen._burn_cached = BurnRate(tokens_per_hour=1234.0, cost_per_day=24.0, hours_in_window=6.0)
    screen._eta_target = now + dt.timedelta(hours=1)
    screen._eta_remaining_tokens_est = 9999.0

    renderable = screen._format_burn_eta_block(now)

    console = Console(width=120, record=True, force_terminal=False, color_system=None)
    console.print(renderable)
    text = console.export_text()

    first_line = next((line for line in text.splitlines() if "成本速率" in line), "")
    assert "github: okwinds/rightcodes-tui-dashboard" in first_line
    assert "Burn:" in first_line

    assert "right.codes 邀请码：4d98a8ea  加返5%" in text
    # 邀请码应跟随在 github 行下方（同一个右侧块）
    idx_github = text.find("github: okwinds/rightcodes-tui-dashboard")
    idx_invite = text.find("right.codes 邀请码：4d98a8ea  加返5%")
    assert 0 <= idx_github < idx_invite
