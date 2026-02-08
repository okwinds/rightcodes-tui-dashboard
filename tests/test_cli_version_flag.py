def test_cli_version_flag_smoke(capsys) -> None:
    """`rightcodes --version` 的最小冒烟测试（离线可跑）。"""
    import pytest

    from rightcodes_tui_dashboard.__main__ import build_parser

    parser = build_parser()

    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--version"])

    assert exc.value.code == 0
    out = capsys.readouterr().out.strip()
    assert out.startswith("rightcodes ")
