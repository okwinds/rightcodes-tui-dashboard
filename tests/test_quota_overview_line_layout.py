from __future__ import annotations


def test_quota_overview_line_keeps_percent_visible_in_narrow_width() -> None:
    from rightcodes_tui_dashboard.ui.app import _quota_overview_line

    t = _quota_overview_line("套餐：$1 / $2  ", 1.0, width=8)
    assert "100%" in t.plain
    assert t.cell_len <= 8


def test_quota_overview_line_respects_cell_width_with_wide_chars() -> None:
    from rightcodes_tui_dashboard.ui.app import _quota_overview_line

    # “套餐：”为宽字符；用 cell_len 计算后不应把右侧百分比挤出屏幕。
    t = _quota_overview_line("套餐：$123 / $456  ", 0.75, width=20)
    assert "75%" in t.plain
    assert t.cell_len <= 20

