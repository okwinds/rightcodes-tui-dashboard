from __future__ import annotations


def test_app_css_sets_background_for_static_sections() -> None:
    """回归护栏：避免 theme 切换时出现“残影/半透明”。

    说明：
    - Textual/Rich 在渲染某些 renderable 时可能不会覆盖整个区域；
      如果该区域没有显式 background，切换主题/重绘可能留下上一帧字符残影。
    - 这里用最轻量的方式断言关键区域具备 background 配置。
    """

    from rightcodes_tui_dashboard.ui.app import RightCodesDashboardApp

    css = RightCodesDashboardApp.CSS
    for selector in (
        "DashboardScreen",
        "#banner",
        "#quota_overview",
        "#body_scroll",
        "#subscriptions",
        "#details_by_model",
        "#use_logs",
        "#burn_eta",
        "#status",
    ):
        assert selector in css
    assert "background: $background" in css


def test_app_forces_repaint_on_theme_change() -> None:
    """回归护栏：主题切换时要强制 repaint，避免偶发残影。"""

    from textual.app import App

    from rightcodes_tui_dashboard.ui.app import RightCodesDashboardApp

    assert RightCodesDashboardApp._watch_theme is not App._watch_theme
