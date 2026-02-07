def test_cli_help_smoke() -> None:
    """`rightcodes --help` 的最小冒烟测试（离线可跑）。"""
    import pytest

    from rightcodes_tui_dashboard.__main__ import build_parser

    parser = build_parser()

    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--help"])

    assert exc.value.code == 0
