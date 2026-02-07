from __future__ import annotations


def test_textual_internal_render_method_not_overridden() -> None:
    """防回归：Screen 不应定义 `_render`，避免覆盖 Textual 内部渲染方法。"""

    from rightcodes_tui_dashboard.ui.app import DashboardScreen, DoctorScreen, LogsScreen

    for cls in (DashboardScreen, LogsScreen, DoctorScreen):
        assert "_render" not in cls.__dict__, f"{cls.__name__} should not define _render"
