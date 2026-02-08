def test_root_help_mentions_dashboard_customization_and_examples(capsys) -> None:
    import pytest

    from rightcodes_tui_dashboard.__main__ import build_parser

    parser = build_parser()

    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--help"])

    assert exc.value.code == 0
    out = capsys.readouterr().out

    assert "rightcodes dashboard --range today --watch 30s --rate-window 6h" in out
    assert "rightcodes dashboard --watch 0s" in out
    assert "rightcodes dashboard --range 7d" in out
    assert "rightcodes <command> --help" in out


def test_dashboard_help_explains_watch_range_and_rate_window(capsys) -> None:
    import pytest

    from rightcodes_tui_dashboard.__main__ import build_parser

    parser = build_parser()

    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["dashboard", "--help"])

    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "--watch" in out
    assert "--range" in out
    assert "--rate-window" in out
    assert "today" in out
